"""
GPU Worker从节点服务（RocketMQ版本） - 从RocketMQ拉取任务执行
"""

import argparse
import time
import threading
from typing import Dict, Any
from datetime import datetime
import numpy as np

try:
    from rocketmq.client import PushConsumer, ConsumeStatus
    ROCKETMQ_AVAILABLE = True
except ImportError:
    ROCKETMQ_AVAILABLE = False
    print("⚠️  RocketMQ客户端未安装")

# 导入自定义模块
from cuda_jit_wrapper import CudaJITWrapper
from gpu_monitor import GPUMonitor
from message_queue_rocketmq import get_message_queue


class GPUWorkerRocketMQ:
    """GPU Worker节点（RocketMQ版本）- 从RocketMQ拉取任务执行"""
    
    def __init__(self, worker_id: str, gpu_device_id: int = 0, gpu_model: str = None,
                 nameserver: str = 'localhost:9876', group_id: str = 'leetgpu_group'):
        """
        初始化GPU Worker
        
        Args:
            worker_id: Worker唯一标识
            gpu_device_id: GPU设备ID
            gpu_model: GPU型号（如'RTX 4090'），Worker只拉取此型号的任务
            nameserver: RocketMQ NameServer地址
            group_id: 消费者组ID
        """
        self.worker_id = worker_id
        self.gpu_device_id = gpu_device_id
        self.gpu_model = gpu_model
        self.cuda_wrapper = CudaJITWrapper()
        self.gpu_monitor = GPUMonitor(simulation_mode=True)
        
        # 初始化消息队列（用于发送结果和心跳）
        self.message_queue = get_message_queue(nameserver, group_id)
        
        # 任务消费者
        self.task_consumer = None
        if ROCKETMQ_AVAILABLE and self.message_queue.connected:
            self._init_task_consumer(nameserver, group_id)
        
        # 当前任务
        self.current_task = None
        self.is_busy = False
        
        # 启动GPU监控
        self.gpu_monitor.start_monitoring(interval=2.0)
        
        # Worker运行状态
        self.running = False
        self.heartbeat_thread = None
        
        print(f"🔧 GPU Worker {worker_id} 已初始化（RocketMQ模式）")
        print(f"   使用GPU设备: {gpu_device_id}")
        print(f"   GPU型号: {gpu_model if gpu_model else '通用（所有型号）'}")
        print(f"   NameServer: {nameserver}")
    
    def _init_task_consumer(self, nameserver: str, group_id: str):
        """初始化任务消费者"""
        try:
            self.task_consumer = PushConsumer(group_id + '_worker_' + self.worker_id)
            self.task_consumer.set_namesrv_addr(nameserver)
            
            # 订阅任务Topic
            # 根据GPU型号订阅特定Tag
            if self.gpu_model:
                tag = self.gpu_model.replace(' ', '_')
                self.task_consumer.subscribe('leetgpu_tasks', self._handle_task_message, tag)
                print(f"📡 订阅 {self.gpu_model} 任务")
            else:
                # 订阅所有任务
                self.task_consumer.subscribe('leetgpu_tasks', self._handle_task_message, '*')
                print(f"📡 订阅所有任务")
            
            self.task_consumer.start()
            print(f"✅ 任务消费者已启动")
            
        except Exception as e:
            print(f"❌ 初始化任务消费者失败: {e}")
            self.task_consumer = None
    
    def _handle_task_message(self, msg):
        """处理任务消息（回调函数）"""
        try:
            # 检查是否正忙
            if self.is_busy:
                print(f"⏸️  Worker正忙，稍后重试")
                return ConsumeStatus.RECONSUME_LATER
            
            # 检查资源
            if not self.check_resources():
                print(f"⏸️  资源不足，稍后重试")
                return ConsumeStatus.RECONSUME_LATER
            
            # 解析任务数据
            import json
            task_data = json.loads(msg.body.decode('utf-8'))
            
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
            
            return ConsumeStatus.CONSUME_SUCCESS
            
        except Exception as e:
            print(f"❌ 处理任务消息失败: {e}")
            self.current_task = None
            self.is_busy = False
            return ConsumeStatus.RECONSUME_LATER
    
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
            return True
    
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
        """启动Worker"""
        if self.running:
            return
        
        self.running = True
        
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self.heartbeat_thread.start()
        
        print(f"✅ Worker {self.worker_id} 已启动，等待任务...")
    
    def stop(self):
        """停止Worker"""
        self.running = False
        
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        
        if self.task_consumer:
            self.task_consumer.shutdown()
        
        self.gpu_monitor.stop_monitoring()
        self.message_queue.shutdown()
        
        print(f"🛑 Worker {self.worker_id} 已停止")
    
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


# 命令行启动
if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='GPU Worker节点（RocketMQ版本）')
    parser.add_argument('--id', type=str, required=True, help='Worker ID')
    parser.add_argument('--gpu', type=int, default=0, help='GPU设备ID')
    parser.add_argument('--gpu-model', type=str, default=None, 
                        help='GPU型号（如RTX 4090），只拉取此型号的任务')
    parser.add_argument('--nameserver', type=str, default='localhost:9876', 
                        help='RocketMQ NameServer地址')
    parser.add_argument('--group-id', type=str, default='leetgpu_group', 
                        help='消费者组ID')
    
    args = parser.parse_args()
    
    # 创建Worker
    worker = GPUWorkerRocketMQ(
        worker_id=args.id,
        gpu_device_id=args.gpu,
        gpu_model=args.gpu_model,
        nameserver=args.nameserver,
        group_id=args.group_id
    )
    
    print("\n" + "="*60)
    print(f"🚀 GPU Worker节点启动（RocketMQ模式）")
    print("="*60)
    print(f"Worker ID: {args.id}")
    print(f"GPU设备: {args.gpu}")
    print(f"NameServer: {args.nameserver}")
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
