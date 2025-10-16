"""
任务队列和分发系统 - 管理GPU任务的提交和分发
"""

import uuid
import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from queue import Queue, Empty
import threading
import json


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
        self.gpu_model = gpu_model  # 指定的GPU型号
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
            'grid_size': self.grid_size,
            'block_size': self.block_size,
            'gpu_model': self.gpu_model,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result,
            'error': self.error,
            'worker_id': self.worker_id
        }


class TaskManager:
    """任务管理器 - 负责任务的提交、分发和状态管理"""
    
    def __init__(self, workers_config: List[Dict]):
        """
        初始化任务管理器
        
        Args:
            workers_config: Worker节点配置列表
        """
        self.workers = workers_config
        self.tasks = {}  # task_id -> Task
        self.task_queue = Queue()
        self.running_tasks = {}  # task_id -> worker_id
        self.worker_status = {w['id']: 'available' for w in workers_config}
        
        # 启动任务分发线程
        self.dispatcher_running = False
        self.dispatcher_thread = None
    
    def submit_task(self, code: str, inputs: List[Any], 
                   grid_size: tuple, block_size: tuple,
                   gpu_model: Optional[str] = None) -> str:
        """
        提交新任务
        
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
        self.task_queue.put(task)
        
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
            return None
        return task.to_dict()
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务状态"""
        return [task.to_dict() for task in self.tasks.values()]
    
    def check_worker_resources(self, worker: Dict) -> bool:
        """
        检查Worker的GPU资源是否可用
        
        Args:
            worker: Worker配置字典
            
        Returns:
            如果资源充足返回True，否则返回False
        """
        try:
            # 查询Worker的GPU状态
            status_url = f"http://{worker['host']}:{worker['port']}/gpu/status"
            response = requests.get(status_url, timeout=2)
            
            if response.status_code == 200:
                gpu_status = response.json()
                
                # 检查显存利用率
                memory_util = gpu_status.get('memory_utilization', 0)
                gpu_util = gpu_status.get('gpu_utilization', 0)
                
                # 从config导入阈值（如果不存在则使用默认值）
                try:
                    from config import GPU_MEMORY_THRESHOLD, GPU_UTILIZATION_THRESHOLD
                except ImportError:
                    GPU_MEMORY_THRESHOLD = 90
                    GPU_UTILIZATION_THRESHOLD = 95
                
                # 如果显存利用率或GPU利用率超过阈值，则不可用
                if memory_util >= GPU_MEMORY_THRESHOLD:
                    print(f"Worker {worker['id']} 显存利用率 {memory_util:.1f}% 超过阈值 {GPU_MEMORY_THRESHOLD}%，任务排队")
                    return False
                
                if gpu_util >= GPU_UTILIZATION_THRESHOLD:
                    print(f"Worker {worker['id']} GPU利用率 {gpu_util:.1f}% 超过阈值 {GPU_UTILIZATION_THRESHOLD}%，任务排队")
                    return False
                
                return True
            else:
                # 无法获取状态，认为不可用
                return False
                
        except Exception as e:
            # 查询失败，认为不可用
            print(f"检查Worker {worker['id']} 资源失败: {e}")
            return False
    
    def find_suitable_worker(self, task: Task) -> Optional[Dict]:
        """
        为任务找到合适的Worker节点
        检查GPU显存和利用率，超过阈值则不分配
        
        Args:
            task: 任务对象
            
        Returns:
            Worker配置字典，如果没有可用Worker则返回None
        """
        # 如果指定了GPU型号，优先选择该型号的Worker
        if task.gpu_model:
            for worker in self.workers:
                if self.worker_status.get(worker['id']) == 'available' and \
                   worker['gpu_model'] == task.gpu_model:
                    # 检查GPU资源是否充足
                    if self.check_worker_resources(worker):
                        return worker
                    else:
                        print(f"Worker {worker['id']} ({worker['gpu_model']}) 资源不足，继续查找...")
        
        # 否则选择任意可用的Worker
        for worker in self.workers:
            if self.worker_status.get(worker['id']) == 'available':
                # 检查GPU资源是否充足
                if self.check_worker_resources(worker):
                    return worker
                else:
                    print(f"Worker {worker['id']} ({worker['gpu_model']}) 资源不足，继续查找...")
        
        return None
    
    def dispatch_task(self, task: Task, worker: Dict) -> bool:
        """
        将任务分发到Worker节点
        
        Args:
            task: 任务对象
            worker: Worker配置
            
        Returns:
            是否分发成功
        """
        try:
            worker_url = f"http://{worker['host']}:{worker['port']}/execute"
            
            payload = {
                'task_id': task.task_id,
                'code': task.code,
                'inputs': task.inputs,
                'grid_size': task.grid_size,
                'block_size': task.block_size
            }
            
            # 发送任务到Worker
            response = requests.post(
                worker_url,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                task.worker_id = worker['id']
                self.running_tasks[task.task_id] = worker['id']
                self.worker_status[worker['id']] = 'busy'
                return True
            else:
                task.status = TaskStatus.FAILED
                task.error = f"Worker返回错误: {response.text}"
                return False
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = f"分发任务失败: {str(e)}"
            return False
    
    def check_task_result(self, task_id: str) -> bool:
        """
        检查任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务是否完成
        """
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False
        
        worker_id = self.running_tasks.get(task_id)
        if not worker_id:
            return False
        
        worker = next((w for w in self.workers if w['id'] == worker_id), None)
        if not worker:
            return False
        
        try:
            result_url = f"http://{worker['host']}:{worker['port']}/result/{task_id}"
            response = requests.get(result_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if data['status'] == 'completed':
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now()
                    task.result = data['result']
                    
                    # 释放Worker
                    self.worker_status[worker_id] = 'available'
                    del self.running_tasks[task_id]
                    return True
                    
                elif data['status'] == 'failed':
                    task.status = TaskStatus.FAILED
                    task.error = data.get('error', 'Unknown error')
                    
                    # 释放Worker
                    self.worker_status[worker_id] = 'available'
                    del self.running_tasks[task_id]
                    return True
                    
        except Exception as e:
            print(f"检查任务结果失败: {e}")
        
        return False
    
    def start_dispatcher(self):
        """启动任务分发器"""
        if self.dispatcher_running:
            return
        
        self.dispatcher_running = True
        self.dispatcher_thread = threading.Thread(
            target=self._dispatcher_loop,
            daemon=True
        )
        self.dispatcher_thread.start()
    
    def stop_dispatcher(self):
        """停止任务分发器"""
        self.dispatcher_running = False
        if self.dispatcher_thread:
            self.dispatcher_thread.join(timeout=5)
    
    def _dispatcher_loop(self):
        """分发器循环"""
        while self.dispatcher_running:
            try:
                # 检查运行中的任务
                for task_id in list(self.running_tasks.keys()):
                    self.check_task_result(task_id)
                
                # 尝试分发队列中的任务
                try:
                    task = self.task_queue.get(timeout=1)
                    
                    # 查找合适的Worker
                    worker = self.find_suitable_worker(task)
                    
                    if worker:
                        # 分发任务
                        self.dispatch_task(task, worker)
                    else:
                        # 没有可用Worker，放回队列
                        self.task_queue.put(task)
                        time.sleep(1)
                        
                except Empty:
                    pass
                    
            except Exception as e:
                print(f"分发器循环错误: {e}")
            
            time.sleep(0.1)
    
    def get_worker_status(self) -> List[Dict]:
        """获取所有Worker的状态"""
        status_list = []
        for worker in self.workers:
            status = {
                'id': worker['id'],
                'name': worker['name'],
                'gpu_model': worker['gpu_model'],
                'status': self.worker_status.get(worker['id'], 'unknown'),
                'host': worker['host'],
                'port': worker['port']
            }
            
            # 尝试ping Worker
            try:
                ping_url = f"http://{worker['host']}:{worker['port']}/health"
                response = requests.get(ping_url, timeout=2)
                status['online'] = response.status_code == 200
            except:
                status['online'] = False
            
            status_list.append(status)
        
        return status_list


# 示例使用
if __name__ == "__main__":
    from config import GPU_WORKERS
    
    # 创建任务管理器
    manager = TaskManager(GPU_WORKERS)
    
    # 启动分发器
    manager.start_dispatcher()
    
    print("任务管理器已启动")
    print(f"配置的Worker节点: {len(GPU_WORKERS)}")
    
    # 获取Worker状态
    worker_status = manager.get_worker_status()
    print("\nWorker状态:")
    for ws in worker_status:
        print(f"  {ws['name']}: {ws['status']} (在线: {ws['online']})")
    
    # 提交示例任务
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
    
    print(f"\n提交任务: {task_id}")
    
    # 等待一段时间
    time.sleep(2)
    
    # 检查任务状态
    status = manager.get_task_status(task_id)
    print(f"任务状态: {status['status']}")
    
    # 停止分发器
    manager.stop_dispatcher()
    print("\n任务管理器已停止")
