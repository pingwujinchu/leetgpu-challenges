"""
消息队列管理模块 - 基于Redis实现主从节点之间的任务通信
"""

import json
import redis
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading


class MessageQueue:
    """消息队列管理器 - 使用Redis作为消息队列后端"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        """
        初始化消息队列
        
        Args:
            host: Redis主机地址
            port: Redis端口
            db: Redis数据库编号
        """
        self.host = host
        self.port = port
        self.db = db
        self.redis_client = None
        self.connected = False
        
        # 队列名称
        self.TASK_QUEUE = 'leetgpu:tasks:queue'
        self.RESULT_PREFIX = 'leetgpu:results:'
        self.WORKER_STATUS_PREFIX = 'leetgpu:workers:status:'
        
        # 连接到Redis
        self._connect()
    
    def _connect(self):
        """连接到Redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self.redis_client.ping()
            self.connected = True
            print(f"✅ 消息队列已连接: redis://{self.host}:{self.port}/{self.db}")
        except Exception as e:
            self.connected = False
            print(f"⚠️  消息队列连接失败: {e}")
            print(f"   使用模拟模式（内存队列）")
            # 使用内存队列作为后备
            self._init_memory_queue()
    
    def _init_memory_queue(self):
        """初始化内存队列（Redis不可用时的后备方案）"""
        from queue import Queue
        self._memory_queue = Queue()
        self._memory_results = {}
        self._memory_worker_status = {}
    
    def push_task(self, task_data: Dict[str, Any]) -> bool:
        """
        推送任务到队列
        
        Args:
            task_data: 任务数据字典
            
        Returns:
            是否推送成功
        """
        try:
            task_json = json.dumps(task_data)
            
            if self.connected:
                # 使用Redis队列
                self.redis_client.rpush(self.TASK_QUEUE, task_json)
                print(f"📤 任务已推送到队列: {task_data['task_id']}")
                return True
            else:
                # 使用内存队列
                self._memory_queue.put(task_data)
                print(f"📤 任务已推送到内存队列: {task_data['task_id']}")
                return True
                
        except Exception as e:
            print(f"❌ 推送任务失败: {e}")
            return False
    
    def pull_task(self, timeout: int = 1) -> Optional[Dict[str, Any]]:
        """
        从队列拉取任务（阻塞）
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            任务数据字典，如果没有任务则返回None
        """
        try:
            if self.connected:
                # 使用Redis队列（阻塞拉取）
                result = self.redis_client.blpop(self.TASK_QUEUE, timeout=timeout)
                if result:
                    _, task_json = result
                    task_data = json.loads(task_json)
                    print(f"📥 从队列拉取任务: {task_data['task_id']}")
                    return task_data
                return None
            else:
                # 使用内存队列
                try:
                    task_data = self._memory_queue.get(timeout=timeout)
                    print(f"📥 从内存队列拉取任务: {task_data['task_id']}")
                    return task_data
                except:
                    return None
                    
        except Exception as e:
            print(f"⚠️  拉取任务失败: {e}")
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
            result_key = f"{self.RESULT_PREFIX}{task_id}"
            result_json = json.dumps(result)
            
            if self.connected:
                self.redis_client.setex(result_key, ttl, result_json)
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
            result_key = f"{self.RESULT_PREFIX}{task_id}"
            
            if self.connected:
                result_json = self.redis_client.get(result_key)
                if result_json:
                    return json.loads(result_json)
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
            status_key = f"{self.WORKER_STATUS_PREFIX}{worker_id}"
            status_json = json.dumps(status)
            
            if self.connected:
                self.redis_client.setex(status_key, ttl, status_json)
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
            status_key = f"{self.WORKER_STATUS_PREFIX}{worker_id}"
            
            if self.connected:
                status_json = self.redis_client.get(status_key)
                if status_json:
                    return json.loads(status_json)
                return None
            else:
                entry = self._memory_worker_status.get(worker_id)
                if entry:
                    # 检查是否过期（超过10秒）
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
            if self.connected:
                # 获取所有Worker状态键
                pattern = f"{self.WORKER_STATUS_PREFIX}*"
                keys = self.redis_client.keys(pattern)
                
                result = {}
                for key in keys:
                    worker_id = key.replace(self.WORKER_STATUS_PREFIX, '')
                    status_json = self.redis_client.get(key)
                    if status_json:
                        result[worker_id] = json.loads(status_json)
                
                return result
            else:
                result = {}
                for worker_id, entry in self._memory_worker_status.items():
                    if time.time() - entry['timestamp'] < 10:
                        result[worker_id] = entry['data']
                return result
                
        except Exception as e:
            print(f"⚠️  获取所有Worker状态失败: {e}")
            return {}
    
    def get_queue_size(self) -> int:
        """
        获取队列中的任务数量
        
        Returns:
            任务数量
        """
        try:
            if self.connected:
                return self.redis_client.llen(self.TASK_QUEUE)
            else:
                return self._memory_queue.qsize()
        except:
            return 0
    
    def clear_queue(self):
        """清空队列（慎用）"""
        try:
            if self.connected:
                self.redis_client.delete(self.TASK_QUEUE)
                print("🗑️  队列已清空")
            else:
                while not self._memory_queue.empty():
                    self._memory_queue.get()
                print("🗑️  内存队列已清空")
        except Exception as e:
            print(f"❌ 清空队列失败: {e}")
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            是否健康
        """
        try:
            if self.connected:
                self.redis_client.ping()
                return True
            return False  # 内存模式认为不健康（无持久化）
        except:
            return False


# 全局消息队列实例
_message_queue_instance = None


def get_message_queue(host: str = 'localhost', port: int = 6379, db: int = 0) -> MessageQueue:
    """
    获取全局消息队列实例（单例模式）
    
    Args:
        host: Redis主机
        port: Redis端口
        db: Redis数据库
        
    Returns:
        MessageQueue实例
    """
    global _message_queue_instance
    
    if _message_queue_instance is None:
        _message_queue_instance = MessageQueue(host, port, db)
    
    return _message_queue_instance


# 示例使用
if __name__ == "__main__":
    # 创建消息队列
    mq = MessageQueue()
    
    print("\n" + "="*60)
    print("消息队列测试")
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
    
    # 查询队列大小
    print(f"队列大小: {mq.get_queue_size()}")
    
    # 拉取任务
    print("\n拉取任务...")
    pulled_task = mq.pull_task(timeout=2)
    if pulled_task:
        print(f"拉取到任务: {pulled_task['task_id']}")
    else:
        print("队列为空")
    
    # 保存结果
    print("\n保存任务结果...")
    result = {
        'status': 'completed',
        'result': [1, 2, 3]
    }
    mq.set_task_result('test-123', result)
    
    # 获取结果
    print("获取任务结果...")
    saved_result = mq.get_task_result('test-123')
    print(f"结果: {saved_result}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
