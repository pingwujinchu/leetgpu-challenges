"""
配置文件 - 定义主从节点信息和GPU资源
"""

# 主节点配置
MASTER_HOST = '0.0.0.0'
MASTER_PORT = 5000

# GPU Worker节点配置
GPU_WORKERS = [
    {
        'id': 'gpu-worker-1',
        'name': 'GPU Worker 1',
        'host': 'localhost',
        'port': 5001,
        'gpu_model': 'RTX 4090',
        'gpu_memory': '24GB',
        'compute_capability': '8.9'
    },
    {
        'id': 'gpu-worker-2',
        'name': 'GPU Worker 2',
        'host': 'localhost',
        'port': 5002,
        'gpu_model': 'A100',
        'gpu_memory': '40GB',
        'compute_capability': '8.0'
    },
    {
        'id': 'gpu-worker-3',
        'name': 'GPU Worker 3',
        'host': 'localhost',
        'port': 5003,
        'gpu_model': 'H100',
        'gpu_memory': '80GB',
        'compute_capability': '9.0'
    }
]

# 任务配置
TASK_TIMEOUT = 300  # 任务超时时间（秒）
MAX_QUEUE_SIZE = 100  # 最大队列大小

# Redis配置（用于任务队列）
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# RocketMQ配置（用于任务队列）
ROCKETMQ_NAMESERVER = 'localhost:9876'
ROCKETMQ_GROUP_ID = 'leetgpu_group'
ROCKETMQ_TASK_TOPIC = 'leetgpu_tasks'
ROCKETMQ_RESULT_TOPIC = 'leetgpu_results'
ROCKETMQ_HEARTBEAT_TOPIC = 'leetgpu_heartbeat'

# 消息队列选择：'redis' 或 'rocketmq'
MESSAGE_QUEUE_TYPE = 'rocketmq'

# GPU监控配置
GPU_MONITOR_INTERVAL = 2  # GPU监控间隔（秒）

# GPU资源限制配置
GPU_MEMORY_THRESHOLD = 90  # 显存利用率阈值（%），超过此值不分配新任务
GPU_UTILIZATION_THRESHOLD = 95  # GPU利用率阈值（%），超过此值不分配新任务
