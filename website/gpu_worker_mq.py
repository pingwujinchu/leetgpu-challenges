"""
GPU Worker从节点服务（消息队列版本） - 从消息队列拉取任务执行
"""

import argparse
import time
import threading
from typing import Dict, Any
from datetime import datetime
import numpy as np

# 导入自定义模块
from cuda_jit_wrapper import CudaJITWrapper
from gpu_monitor import GPUMonitor
from message_queue import get_message_queue


class GPUWorkerMQ:
    """GPU Worker节点（消息队列版本）- 从消息队列拉取任务执行"""
    
    def __init__(self, worker_id: str, gpu_device_id: int = 0,
                 redis_host: str = 'localhost', redis_port: int = 6379, redis_db: int = 0):
        """
        初始化GPU Worker
        
        Args:
            worker_id: Worker唯一标识
            gpu_device_id: GPU设备ID
            redis_host: Redis主机地址
            redis_port: Redis端口
            redis_db: Redis数据库编号
        """
        self.worker_id = worker_id
        self.gpu_device_id = gpu_device_id
        self.cuda_wrapper = CudaJITWrapper()
        self.gpu_monitor = GPUMonitor(simulation_mode=True)  # 默认使用模拟模式
        
        # 初始化消息队列
        self.message_queue = get_message_queue(redis_host, redis_port, redis_db)
        
        # 当前任务
        self.current_task = None
        self.is_busy = False
        
        # 启动GPU监控
        self.gpu_monitor.start_monitoring(interval=2.0)
        
        # Worker运行状态
        self.running = False
        self.worker_thread = None
        self.heartbeat_thread = None
        
        print(f"🔧 GPU Worker {worker_id} 已初始化（消息队列模式）")
        print(f"   使用GPU设备: {gpu_device_id}")
        print(f"   队列后端: {'Redis' if self.message_queue.connected else '内存模式'}")
    
    def check_resources(self) -> bool:
        """
        检查GPU资源是否充足
        
        Returns:
            资源是否充足
        """
        try:
            gpu_status = self.gpu_monitor.get_gpu_utilization(self.gpu_device_id)
            
            memory_util = gpu_status.get('memory_utilization', 0)
            gpu_util = gpu_status.get('gpu_utilization', 0)
            
            # 从config导入阈值
            try:
                from config import GPU_MEMORY_THRESHOLD, GPU_UTILIZATION_THRESHOLD
            except ImportError:
                GPU_MEMORY_THRESHOLD = 90
                GPU_UTILIZATION_THRESHOLD = 95
            
            # 检查是否超过阈值
            if memory_util >= GPU_MEMORY_THRESHOLD:
                print(f"⚠️  显存利用率 {memory_util:.1f}% 超过阈值 {GPU_MEMORY_THRESHOLD}%")
                return False
            
            if gpu_util >= GPU_UTILIZATION_THRESHOLD:
                print(f"⚠️  GPU利用率 {gpu_util:.1f}% 超过阈值 {GPU_UTILIZATION_THRESHOLD}%")
                return False
            
            return True
            
        except Exception as e:
            print(f"⚠️  检查资源失败: {e}")
            return True  # 检查失败时假设资源充足
    
    def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行GPU任务
        
        Args:
            task_data: 任务数据字典
            
        Returns:
            执行结果字典
        """
        task_id = task_data.get('task_id')
        code = task_data.get('code')
        inputs_data = task_data.get('inputs', [])
        grid_size = tuple(task_data.get('grid_size', [1]))
        block_size = tuple(task_data.get('block_size', [1]))
        
        result = {
            'task_id': task_id,
            'worker_id': self.worker_id,
            'status': 'running',
            'started_at': datetime.now().isoformat()
        }
        
        # 保存初始结果（运行中状态）
        self.message_queue.set_task_result(task_id, result)
        
        try:
            # 验证代码
            is_valid, msg = self.cuda_wrapper.validate_cuda_code(code)
            if not is_valid:
                result['status'] = 'failed'
                result['error'] = f"代码验证失败: {msg}"
                result['completed_at'] = datetime.now().isoformat()
                self.message_queue.set_task_result(task_id, result)
                return result
            
            # 编译内核
            try:
                kernel = self.cuda_wrapper.wrap_kernel(code)
            except Exception as e:
                result['status'] = 'failed'
                result['error'] = f"内核编译失败: {str(e)}"
                result['completed_at'] = datetime.now().isoformat()
                self.message_queue.set_task_result(task_id, result)
                return result
            
            # 准备输入数据
            inputs = []
            for inp in inputs_data:
                if isinstance(inp, dict) and 'data' in inp:
                    # 从字典中恢复numpy数组
                    arr = np.array(inp['data'], dtype=inp.get('dtype', 'float32'))
                    if 'shape' in inp:
                        arr = arr.reshape(inp['shape'])
                    inputs.append(arr)
                else:
                    inputs.append(inp)
            
            # 执行内核
            if inputs:
                try:
                    outputs = self.cuda_wrapper.execute_kernel(
                        kernel, inputs, grid_size, block_size
                    )
                    
                    # 将numpy数组转换为可序列化的格式
                    serializable_outputs = []
                    for out in outputs:
                        if isinstance(out, np.ndarray):
                            serializable_outputs.append({
                                'data': out.tolist(),
                                'shape': out.shape,
                                'dtype': str(out.dtype)
                            })
                        else:
                            serializable_outputs.append(out)
                    
                    result['status'] = 'completed'
                    result['result'] = serializable_outputs
                    result['completed_at'] = datetime.now().isoformat()
                    
                except Exception as e:
                    result['status'] = 'failed'
                    result['error'] = f"内核执行失败: {str(e)}"
                    result['completed_at'] = datetime.now().isoformat()
            else:
                result['status'] = 'completed'
                result['result'] = {'message': '任务已提交，但没有输入数据'}
                result['completed_at'] = datetime.now().isoformat()
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = f"执行任务时发生错误: {str(e)}"
            result['completed_at'] = datetime.now().isoformat()
        
        # 保存最终结果
        self.message_queue.set_task_result(task_id, result)
        return result
    
    def start(self):
        """启动Worker（开始从队列拉取任务）"""
        if self.running:
            return
        
        self.running = True
        
        # 启动工作线程
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True
        )
        self.worker_thread.start()
        
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self.heartbeat_thread.start()
        
        print(f"✅ Worker {self.worker_id} 已启动，开始拉取任务...")
    
    def stop(self):
        """停止Worker"""
        self.running = False
        
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        
        self.gpu_monitor.stop_monitoring()
        
        print(f"🛑 Worker {self.worker_id} 已停止")
    
    def _worker_loop(self):
        """工作循环 - 持续从队列拉取任务"""
        while self.running:
            try:
                # 检查资源是否充足
                if not self.check_resources():
                    print(f"⏸️  资源不足，等待...")
                    time.sleep(5)
                    continue
                
                # 从消息队列拉取任务（阻塞1秒）
                task_data = self.message_queue.pull_task(timeout=1)
                
                if task_data:
                    self.is_busy = True
                    self.current_task = task_data['task_id']
                    
                    print(f"🎯 开始执行任务: {self.current_task}")
                    
                    # 执行任务
                    result = self.execute_task(task_data)
                    
                    if result['status'] == 'completed':
                        print(f"✅ 任务完成: {self.current_task}")
                    else:
                        print(f"❌ 任务失败: {self.current_task} - {result.get('error', 'Unknown')}")
                    
                    self.current_task = None
                    self.is_busy = False
                
            except Exception as e:
                print(f"❌ Worker循环错误: {e}")
                self.current_task = None
                self.is_busy = False
            
            time.sleep(0.1)
    
    def _heartbeat_loop(self):
        """心跳循环 - 定期更新Worker状态到消息队列"""
        while self.running:
            try:
                # 获取GPU状态
                gpu_status = self.gpu_monitor.get_gpu_utilization(self.gpu_device_id)
                
                # 构建状态数据
                status = {
                    'worker_id': self.worker_id,
                    'status': 'busy' if self.is_busy else 'available',
                    'current_task': self.current_task,
                    'gpu_utilization': gpu_status.get('gpu_utilization', 0),
                    'memory_utilization': gpu_status.get('memory_utilization', 0),
                    'temperature': gpu_status.get('temperature', 0),
                    'power_usage': gpu_status.get('power_usage', 0),
                    'timestamp': datetime.now().isoformat()
                }
                
                # 更新到消息队列
                self.message_queue.update_worker_status(self.worker_id, status, ttl=10)
                
            except Exception as e:
                print(f"⚠️  心跳更新失败: {e}")
            
            time.sleep(5)  # 每5秒发送一次心跳


# 示例使用和命令行启动
if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='GPU Worker节点（消息队列版本）')
    parser.add_argument('--id', type=str, required=True, help='Worker ID')
    parser.add_argument('--gpu', type=int, default=0, help='GPU设备ID')
    parser.add_argument('--redis-host', type=str, default='localhost', help='Redis主机')
    parser.add_argument('--redis-port', type=int, default=6379, help='Redis端口')
    parser.add_argument('--redis-db', type=int, default=0, help='Redis数据库')
    
    args = parser.parse_args()
    
    # 创建Worker
    worker = GPUWorkerMQ(
        worker_id=args.id,
        gpu_device_id=args.gpu,
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        redis_db=args.redis_db
    )
    
    print("\n" + "="*60)
    print(f"🚀 GPU Worker节点启动（消息队列模式）")
    print("="*60)
    print(f"Worker ID: {args.id}")
    print(f"GPU设备: {args.gpu}")
    print(f"Redis: {args.redis_host}:{args.redis_port}/{args.redis_db}")
    print("="*60 + "\n")
    
    # 启动Worker
    worker.start()
    
    try:
        # 保持运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n收到停止信号...")
        worker.stop()
        print("Worker已停止")
