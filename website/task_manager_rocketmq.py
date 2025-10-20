"""
任务管理器（RocketMQ版本） - 基于RocketMQ的任务管理
主节点通过RocketMQ推送任务，从节点拉取任务执行
"""

import uuid
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import threading

from message_queue_rocketmq import get_message_queue


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Task:
    """任务对象"""
    
    def __init__(self, task_id: str, code: str, inputs: List[Any],
                 grid_size: tuple, block_size: tuple, gpu_model: Optional[str] = None):
        self.task_id = task_id
        self.code = code
        self.inputs = inputs
        self.grid_size = grid_size
        self.block_size = block_size
        self.gpu_model = gpu_model
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.worker_id = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'code': self.code,
            'inputs': self.inputs,
            'grid_size': list(self.grid_size),
            'block_size': list(self.block_size),
            'gpu_model': self.gpu_model,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result,
            'error': self.error,
            'worker_id': self.worker_id
        }


class TaskManagerRocketMQ:
    """任务管理器（RocketMQ版本）- 主节点推送任务，从节点拉取执行"""
    
    def __init__(self, workers_config: List[Dict], nameserver: str = 'localhost:9876',
                 group_id: str = 'leetgpu_group'):
        """
        初始化任务管理器
        
        Args:
            workers_config: Worker节点配置列表
            nameserver: RocketMQ NameServer地址
            group_id: 消费者组ID
        """
        self.workers = workers_config
        self.tasks = {}  # task_id -> Task
        
        # 初始化消息队列
        self.message_queue = get_message_queue(nameserver, group_id)
        
        print(f"📮 任务管理器已初始化（RocketMQ模式）")
        print(f"   队列后端: {'RocketMQ' if self.message_queue.connected else '内存模式'}")
        
        # 启动结果监控线程
        self.monitor_running = False
        self.monitor_thread = None
    
    def submit_task(self, code: str, inputs: List[Any], 
                   grid_size: tuple, block_size: tuple,
                   gpu_model: Optional[str] = None) -> str:
        """
        提交新任务到RocketMQ
        
        Args:
            code: CUDA代码
            inputs: 输入数据
            grid_size: Grid大小
            block_size: Block大小
            gpu_model: 指定的GPU型号（可选）
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        task = Task(task_id, code, inputs, grid_size, block_size, gpu_model)
        
        self.tasks[task_id] = task
        task.status = TaskStatus.QUEUED
        
        # 准备任务数据
        task_data = {
            'task_id': task.task_id,
            'code': task.code,
            'inputs': task.inputs,
            'grid_size': list(task.grid_size),
            'block_size': list(task.block_size),
            'gpu_model': task.gpu_model,
            'created_at': task.created_at.isoformat()
        }
        
        # 推送到RocketMQ（根据GPU型号路由）
        success = self.message_queue.push_task(task_data, gpu_model=gpu_model)
        
        if success:
            if gpu_model:
                print(f"✅ 任务 {task_id} 已推送到 {gpu_model} 队列")
            else:
                print(f"✅ 任务 {task_id} 已推送到通用队列")
        else:
            print(f"❌ 任务 {task_id} 推送失败")
            task.status = TaskStatus.FAILED
            task.error = "推送到消息队列失败"
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态字典
        """
        task = self.tasks.get(task_id)
        if not task:
            # 尝试从消息队列获取结果
            result = self.message_queue.get_task_result(task_id)
            if result:
                return result
            return None
        
        # 检查是否有新结果
        result = self.message_queue.get_task_result(task_id)
        if result and task.status in [TaskStatus.QUEUED, TaskStatus.RUNNING]:
            # 更新任务状态
            self._update_task_from_result(task, result)
        
        return task.to_dict()
    
    def _update_task_from_result(self, task: Task, result: Dict):
        """从结果更新任务状态"""
        if result['status'] == 'running':
            task.status = TaskStatus.RUNNING
            if not task.started_at and result.get('started_at'):
                task.started_at = datetime.fromisoformat(result['started_at'])
            task.worker_id = result.get('worker_id')
            
        elif result['status'] == 'completed':
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result.get('result')
            task.worker_id = result.get('worker_id')
            
        elif result['status'] == 'failed':
            task.status = TaskStatus.FAILED
            task.error = result.get('error', 'Unknown error')
            task.worker_id = result.get('worker_id')
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务状态"""
        return [task.to_dict() for task in self.tasks.values()]
    
    def get_queue_size(self) -> int:
        """获取队列中的任务数量"""
        return self.message_queue.get_queue_size()
    
    def get_worker_status(self) -> List[Dict]:
        """
        获取所有Worker的状态（从消息队列的心跳信息）
        
        Returns:
            Worker状态列表
        """
        # 从消息队列获取Worker心跳状态
        worker_status_map = self.message_queue.get_all_worker_status()
        
        status_list = []
        for worker in self.workers:
            worker_id = worker['id']
            status_data = worker_status_map.get(worker_id, {})
            
            status = {
                'id': worker['id'],
                'name': worker['name'],
                'gpu_model': worker['gpu_model'],
                'gpu_memory': worker['gpu_memory'],
                'compute_capability': worker['compute_capability'],
                'host': worker['host'],
                'port': worker['port'],
                'online': worker_id in worker_status_map,
                'status': status_data.get('status', 'unknown'),
                'current_task': status_data.get('current_task'),
                'last_heartbeat': status_data.get('timestamp')
            }
            
            status_list.append(status)
        
        return status_list
    
    def start_monitor(self):
        """启动结果监控线程"""
        if self.monitor_running:
            return
        
        self.monitor_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()
        print("📊 结果监控线程已启动")
    
    def stop_monitor(self):
        """停止结果监控线程"""
        self.monitor_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("📊 结果监控线程已停止")
    
    def _monitor_loop(self):
        """监控循环 - 定期检查任务结果"""
        while self.monitor_running:
            try:
                # 检查所有未完成任务的状态
                for task_id, task in list(self.tasks.items()):
                    if task.status in [TaskStatus.QUEUED, TaskStatus.RUNNING]:
                        result = self.message_queue.get_task_result(task_id)
                        if result:
                            self._update_task_from_result(task, result)
                
                time.sleep(2)  # 每2秒检查一次
                
            except Exception as e:
                print(f"⚠️  监控循环错误: {e}")
            
            time.sleep(0.1)
    
    def clear_queue(self):
        """清空队列（慎用）"""
        self.message_queue.clear_queue()
    
    def health_check(self) -> Dict:
        """
        健康检查
        
        Returns:
            健康状态字典
        """
        return {
            'message_queue': self.message_queue.health_check(),
            'queue_size': self.get_queue_size(),
            'total_tasks': len(self.tasks),
            'workers_online': sum(1 for w in self.get_worker_status() if w['online'])
        }
    
    def shutdown(self):
        """关闭任务管理器"""
        self.stop_monitor()
        self.message_queue.shutdown()


# 示例使用
if __name__ == "__main__":
    from config import GPU_WORKERS, ROCKETMQ_NAMESERVER, ROCKETMQ_GROUP_ID
    
    # 创建任务管理器
    manager = TaskManagerRocketMQ(GPU_WORKERS, ROCKETMQ_NAMESERVER, ROCKETMQ_GROUP_ID)
    
    # 启动监控
    manager.start_monitor()
    
    print("\n" + "="*60)
    print("任务管理器已启动（RocketMQ模式）")
    print("="*60)
    print(f"配置的Worker节点: {len(GPU_WORKERS)}")
    
    # 健康检查
    health = manager.health_check()
    print(f"\n健康状态:")
    print(f"  消息队列: {'✅' if health['message_queue'] else '❌'}")
    print(f"  队列大小: {health['queue_size']}")
    print(f"  在线Worker: {health['workers_online']}")
    
    # 获取Worker状态
    worker_status = manager.get_worker_status()
    print("\nWorker状态:")
    for ws in worker_status:
        status_icon = "✅" if ws['online'] else "❌"
        print(f"  {status_icon} {ws['name']}: {ws['status']}")
    
    # 提交示例任务
    print("\n提交测试任务...")
    sample_code = """
def vector_add(a, b, c):
    idx = cuda.grid(1)
    if idx < c.size:
        c[idx] = a[idx] + b[idx]
"""
    
    task_id = manager.submit_task(
        code=sample_code,
        inputs=[],
        grid_size=(32,),
        block_size=(32,),
        gpu_model="RTX 4090"
    )
    
    print(f"任务ID: {task_id}")
    print(f"队列大小: {manager.get_queue_size()}")
    
    # 等待一段时间
    print("\n等待3秒...")
    time.sleep(3)
    
    # 检查任务状态
    status = manager.get_task_status(task_id)
    if status:
        print(f"任务状态: {status['status']}")
    
    # 停止
    manager.shutdown()
    print("\n任务管理器已停止")
