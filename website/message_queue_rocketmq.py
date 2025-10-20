"""
消息队列管理模块 - 基于RocketMQ实现主从节点之间的任务通信
"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading

try:
    from rocketmq.client import Producer, PushConsumer, ConsumeStatus, Message
    ROCKETMQ_AVAILABLE = True
except ImportError:
    ROCKETMQ_AVAILABLE = False
    print("⚠️  RocketMQ客户端未安装，请运行: pip install rocketmq-client-python")


class MessageQueueRocketMQ:
    """消息队列管理器 - 使用RocketMQ作为消息队列后端"""
    
    def __init__(self, nameserver: str = 'localhost:9876', group_id: str = 'leetgpu_group'):
        """
        初始化消息队列
        
        Args:
            nameserver: RocketMQ NameServer地址
            group_id: 消费者组ID
        """
        self.nameserver = nameserver
        self.group_id = group_id
        self.connected = False
        
        # Topic和Tag配置
        self.TASK_TOPIC = 'leetgpu_tasks'
        self.RESULT_TOPIC = 'leetgpu_results'
        self.HEARTBEAT_TOPIC = 'leetgpu_heartbeat'
        
        # 内存存储（用于结果和状态查询）
        self._results_cache = {}
        self._worker_status_cache = {}
        self._cache_lock = threading.Lock()
        
        # Producer和Consumer
        self.producer = None
        self.result_consumer = None
        self.heartbeat_consumer = None
        
        # 连接到RocketMQ
        self._connect()
    
    def _connect(self):
        """连接到RocketMQ"""
        if not ROCKETMQ_AVAILABLE:
            self.connected = False
            print(f"⚠️  RocketMQ客户端未安装，使用模拟模式（内存队列）")
            self._init_memory_queue()
            return
        
        try:
            # 创建Producer
            self.producer = Producer(self.group_id + '_producer')
            self.producer.set_namesrv_addr(self.nameserver)
            self.producer.start()
            
            # 创建结果消费者（用于缓存结果）
            self.result_consumer = PushConsumer(self.group_id + '_result_consumer')
            self.result_consumer.set_namesrv_addr(self.nameserver)
            self.result_consumer.subscribe(self.RESULT_TOPIC, self._handle_result_message)
            self.result_consumer.start()
            
            # 创建心跳消费者（用于缓存Worker状态）
            self.heartbeat_consumer = PushConsumer(self.group_id + '_heartbeat_consumer')
            self.heartbeat_consumer.set_namesrv_addr(self.nameserver)
            self.heartbeat_consumer.subscribe(self.HEARTBEAT_TOPIC, self._handle_heartbeat_message)
            self.heartbeat_consumer.start()
            
            self.connected = True
            print(f"✅ 消息队列已连接: RocketMQ@{self.nameserver}")
            
        except Exception as e:
            self.connected = False
            print(f"⚠️  消息队列连接失败: {e}")
            print(f"   使用模拟模式（内存队列）")
            self._init_memory_queue()
    
    def _init_memory_queue(self):
        """初始化内存队列（RocketMQ不可用时的后备方案）"""
        from queue import Queue
        self._memory_queue = Queue()
        self._memory_results = {}
        self._memory_worker_status = {}
    
    def _handle_result_message(self, msg):
        """处理结果消息（回调函数）"""
        try:
            result_data = json.loads(msg.body.decode('utf-8'))
            task_id = result_data.get('task_id')
            
            if task_id:
                with self._cache_lock:
                    self._results_cache[task_id] = {
                        'data': result_data,
                        'timestamp': time.time()
                    }
                print(f"📥 收到任务结果: {task_id}")
            
            return ConsumeStatus.CONSUME_SUCCESS
        except Exception as e:
            print(f"❌ 处理结果消息失败: {e}")
            return ConsumeStatus.RECONSUME_LATER
    
    def _handle_heartbeat_message(self, msg):
        """处理心跳消息（回调函数）"""
        try:
            status_data = json.loads(msg.body.decode('utf-8'))
            worker_id = status_data.get('worker_id')
            
            if worker_id:
                with self._cache_lock:
                    self._worker_status_cache[worker_id] = {
                        'data': status_data,
                        'timestamp': time.time()
                    }
            
            return ConsumeStatus.CONSUME_SUCCESS
        except Exception as e:
            print(f"❌ 处理心跳消息失败: {e}")
            return ConsumeStatus.RECONSUME_LATER
    
    def push_task(self, task_data: Dict[str, Any], gpu_model: str = None) -> bool:
        """
        推送任务到队列（支持GPU型号路由）
        
        Args:
            task_data: 任务数据字典
            gpu_model: 指定的GPU型号，如果为None则推送到通用队列
            
        Returns:
            是否推送成功
        """
        try:
            task_json = json.dumps(task_data)
            
            # 确定Tag（用于GPU型号路由）
            if gpu_model:
                tag = gpu_model.replace(' ', '_')
                print(f"📤 任务推送到 {gpu_model} 队列: {task_data['task_id']}")
            else:
                tag = 'GENERAL'
                print(f"📤 任务推送到通用队列: {task_data['task_id']}")
            
            if self.connected:
                # 创建RocketMQ消息
                msg = Message(self.TASK_TOPIC)
                msg.set_body(task_json.encode('utf-8'))
                msg.set_tags(tag)
                msg.set_keys(task_data['task_id'])
                
                # 发送消息
                result = self.producer.send_sync(msg)
                return result.status == 0  # 0表示成功
            else:
                # 使用内存队列
                self._memory_queue.put(task_data)
                print(f"📤 任务已推送到内存队列: {task_data['task_id']}")
                return True
                
        except Exception as e:
            print(f"❌ 推送任务失败: {e}")
            return False
    
    def pull_task(self, gpu_models: list = None, timeout: int = 1) -> Optional[Dict[str, Any]]:
        """
        从队列拉取任务（支持GPU型号过滤）
        Worker可以指定支持的GPU型号，只拉取匹配的任务
        
        Args:
            gpu_models: 支持的GPU型号列表，例如 ['RTX 4090', 'RTX 4080']
                       如果为None，则从通用队列拉取
            timeout: 超时时间（秒）
            
        Returns:
            任务数据字典，如果没有任务则返回None
        """
        # 注意: RocketMQ通常使用Push模式，这里我们需要在Worker端创建Consumer
        # 这个方法主要用于内存队列模式
        if not self.connected:
            try:
                task_data = self._memory_queue.get(timeout=timeout)
                print(f"📥 从内存队列拉取任务: {task_data['task_id']}")
                return task_data
            except:
                return None
        
        # RocketMQ模式下，任务通过Push Consumer处理，不使用pull模式
        # 这里返回None，实际的任务处理在Worker的Consumer回调中进行
        return None
    
    def set_task_result(self, task_id: str, result: Dict[str, Any], ttl: int = 3600):
        """
        保存任务结果
        
        Args:
            task_id: 任务ID
            result: 结果数据
            ttl: 结果保存时间（秒），默认1小时
        """
        try:
            result_json = json.dumps(result)
            
            if self.connected:
                # 发送结果到RocketMQ
                msg = Message(self.RESULT_TOPIC)
                msg.set_body(result_json.encode('utf-8'))
                msg.set_keys(task_id)
                
                self.producer.send_sync(msg)
                
                # 同时缓存到本地
                with self._cache_lock:
                    self._results_cache[task_id] = {
                        'data': result,
                        'timestamp': time.time()
                    }
                
                print(f"💾 任务结果已保存: {task_id}")
            else:
                self._memory_results[task_id] = result
                print(f"💾 任务结果已保存到内存: {task_id}")
                
        except Exception as e:
            print(f"❌ 保存任务结果失败: {e}")
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            结果数据字典，如果不存在则返回None
        """
        try:
            if self.connected:
                # 从缓存获取
                with self._cache_lock:
                    cached = self._results_cache.get(task_id)
                    if cached:
                        # 检查是否过期（默认1小时）
                        if time.time() - cached['timestamp'] < 3600:
                            return cached['data']
                        else:
                            # 清理过期数据
                            del self._results_cache[task_id]
                return None
            else:
                return self._memory_results.get(task_id)
                
        except Exception as e:
            print(f"⚠️  获取任务结果失败: {e}")
            return None
    
    def update_worker_status(self, worker_id: str, status: Dict[str, Any], ttl: int = 10):
        """
        更新Worker状态（心跳）
        
        Args:
            worker_id: Worker ID
            status: 状态数据
            ttl: 状态保存时间（秒），默认10秒
        """
        try:
            status_json = json.dumps(status)
            
            if self.connected:
                # 发送心跳到RocketMQ
                msg = Message(self.HEARTBEAT_TOPIC)
                msg.set_body(status_json.encode('utf-8'))
                msg.set_keys(worker_id)
                
                self.producer.send_sync(msg)
                
                # 同时缓存到本地
                with self._cache_lock:
                    self._worker_status_cache[worker_id] = {
                        'data': status,
                        'timestamp': time.time()
                    }
            else:
                self._memory_worker_status[worker_id] = {
                    'data': status,
                    'timestamp': time.time()
                }
                
        except Exception as e:
            print(f"⚠️  更新Worker状态失败: {e}")
    
    def get_worker_status(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        获取Worker状态
        
        Args:
            worker_id: Worker ID
            
        Returns:
            状态数据字典，如果不存在则返回None
        """
        try:
            if self.connected:
                with self._cache_lock:
                    cached = self._worker_status_cache.get(worker_id)
                    if cached:
                        # 检查是否过期（10秒）
                        if time.time() - cached['timestamp'] < 10:
                            return cached['data']
                        else:
                            del self._worker_status_cache[worker_id]
                return None
            else:
                entry = self._memory_worker_status.get(worker_id)
                if entry:
                    if time.time() - entry['timestamp'] < 10:
                        return entry['data']
                return None
                
        except Exception as e:
            print(f"⚠️  获取Worker状态失败: {e}")
            return None
    
    def get_all_worker_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有Worker状态
        
        Returns:
            Worker状态字典 {worker_id: status}
        """
        try:
            result = {}
            
            if self.connected:
                with self._cache_lock:
                    current_time = time.time()
                    # 清理过期数据并返回有效数据
                    expired_keys = []
                    for worker_id, cached in self._worker_status_cache.items():
                        if current_time - cached['timestamp'] < 10:
                            result[worker_id] = cached['data']
                        else:
                            expired_keys.append(worker_id)
                    
                    # 清理过期键
                    for key in expired_keys:
                        del self._worker_status_cache[key]
            else:
                for worker_id, entry in self._memory_worker_status.items():
                    if time.time() - entry['timestamp'] < 10:
                        result[worker_id] = entry['data']
            
            return result
                
        except Exception as e:
            print(f"⚠️  获取所有Worker状态失败: {e}")
            return {}
    
    def get_queue_size(self, gpu_model: str = None) -> int:
        """
        获取队列中的任务数量
        
        Args:
            gpu_model: GPU型号，如果为None则返回通用队列大小
            
        Returns:
            任务数量
        """
        # RocketMQ没有直接的API获取队列长度
        # 这里返回0，实际使用中可以通过RocketMQ管理界面查看
        if not self.connected:
            return self._memory_queue.qsize()
        return 0
    
    def get_all_queue_sizes(self) -> Dict[str, int]:
        """
        获取所有队列的大小
        
        Returns:
            队列大小字典 {queue_name: size}
        """
        if not self.connected:
            return {'内存队列': self._memory_queue.qsize()}
        
        # RocketMQ模式下返回估计值
        return {'RocketMQ': 0}  # 需要通过管理API查询
    
    def clear_queue(self):
        """清空队列（慎用）"""
        try:
            if not self.connected:
                while not self._memory_queue.empty():
                    self._memory_queue.get()
                print("🗑️  内存队列已清空")
            else:
                print("⚠️  RocketMQ队列清空需要通过管理工具操作")
        except Exception as e:
            print(f"❌ 清空队列失败: {e}")
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            是否健康
        """
        try:
            if self.connected and self.producer:
                # 简单的健康检查
                return True
            return False
        except:
            return False
    
    def shutdown(self):
        """关闭连接"""
        try:
            if self.connected:
                if self.producer:
                    self.producer.shutdown()
                if self.result_consumer:
                    self.result_consumer.shutdown()
                if self.heartbeat_consumer:
                    self.heartbeat_consumer.shutdown()
                print("✅ RocketMQ连接已关闭")
        except Exception as e:
            print(f"⚠️  关闭RocketMQ连接失败: {e}")


# 全局消息队列实例
_message_queue_instance = None


def get_message_queue(nameserver: str = 'localhost:9876', 
                     group_id: str = 'leetgpu_group') -> MessageQueueRocketMQ:
    """
    获取全局消息队列实例（单例模式）
    
    Args:
        nameserver: RocketMQ NameServer地址
        group_id: 消费者组ID
        
    Returns:
        MessageQueueRocketMQ实例
    """
    global _message_queue_instance
    
    if _message_queue_instance is None:
        _message_queue_instance = MessageQueueRocketMQ(nameserver, group_id)
    
    return _message_queue_instance


# 示例使用
if __name__ == "__main__":
    # 创建消息队列
    mq = MessageQueueRocketMQ()
    
    print("\n" + "="*60)
    print("消息队列测试 (RocketMQ)")
    print("="*60)
    
    # 健康检查
    print(f"\n健康检查: {'✅' if mq.health_check() else '❌'}")
    print(f"连接状态: {'已连接' if mq.connected else '未连接（内存模式）'}")
    
    # 推送任务
    print("\n推送测试任务...")
    task = {
        'task_id': 'test-123',
        'code': 'def test(): pass',
        'inputs': [],
        'grid_size': [1],
        'block_size': [1]
    }
    mq.push_task(task)
    
    # 保存结果
    print("\n保存任务结果...")
    result = {
        'status': 'completed',
        'result': [1, 2, 3]
    }
    mq.set_task_result('test-123', result)
    
    # 等待结果传播
    time.sleep(1)
    
    # 获取结果
    print("获取任务结果...")
    saved_result = mq.get_task_result('test-123')
    print(f"结果: {saved_result}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    
    # 关闭连接
    mq.shutdown()
