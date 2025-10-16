"""
多GPU配置示例
每台GPU服务器可以有多张GPU卡，每张卡运行一个Worker
"""

# 主节点配置
MASTER_HOST = '0.0.0.0'
MASTER_PORT = 5000

# Redis配置（主节点）
REDIS_HOST = '192.168.1.100'  # 主节点IP
REDIS_PORT = 6379
REDIS_DB = 0

# ============================================================
# GPU Worker配置 - 多GPU示例
# ============================================================

GPU_WORKERS = [
    # GPU机器1 (192.168.1.101) - 4张RTX 4090
    {
        'id': 'gpu-server-1-gpu-0',
        'name': 'GPU Server 1 - GPU 0',
        'host': '192.168.1.101',
        'port': 5001,
        'gpu_device_id': 0,
        'gpu_model': 'RTX 4090',
        'gpu_memory': '24GB',
        'compute_capability': '8.9'
    },
    {
        'id': 'gpu-server-1-gpu-1',
        'name': 'GPU Server 1 - GPU 1',
        'host': '192.168.1.101',
        'port': 5002,
        'gpu_device_id': 1,
        'gpu_model': 'RTX 4090',
        'gpu_memory': '24GB',
        'compute_capability': '8.9'
    },
    {
        'id': 'gpu-server-1-gpu-2',
        'name': 'GPU Server 1 - GPU 2',
        'host': '192.168.1.101',
        'port': 5003,
        'gpu_device_id': 2,
        'gpu_model': 'RTX 4090',
        'gpu_memory': '24GB',
        'compute_capability': '8.9'
    },
    {
        'id': 'gpu-server-1-gpu-3',
        'name': 'GPU Server 1 - GPU 3',
        'host': '192.168.1.101',
        'port': 5004,
        'gpu_device_id': 3,
        'gpu_model': 'RTX 4090',
        'gpu_memory': '24GB',
        'compute_capability': '8.9'
    },
    
    # GPU机器2 (192.168.1.102) - 8张A100
    {
        'id': 'gpu-server-2-gpu-0',
        'name': 'GPU Server 2 - GPU 0',
        'host': '192.168.1.102',
        'port': 5001,
        'gpu_device_id': 0,
        'gpu_model': 'A100',
        'gpu_memory': '80GB',
        'compute_capability': '8.0'
    },
    {
        'id': 'gpu-server-2-gpu-1',
        'name': 'GPU Server 2 - GPU 1',
        'host': '192.168.1.102',
        'port': 5002,
        'gpu_device_id': 1,
        'gpu_model': 'A100',
        'gpu_memory': '80GB',
        'compute_capability': '8.0'
    },
    {
        'id': 'gpu-server-2-gpu-2',
        'name': 'GPU Server 2 - GPU 2',
        'host': '192.168.1.102',
        'port': 5003,
        'gpu_device_id': 2,
        'gpu_model': 'A100',
        'gpu_memory': '80GB',
        'compute_capability': '8.0'
    },
    {
        'id': 'gpu-server-2-gpu-3',
        'name': 'GPU Server 2 - GPU 3',
        'host': '192.168.1.102',
        'port': 5004,
        'gpu_device_id': 3,
        'gpu_model': 'A100',
        'gpu_memory': '80GB',
        'compute_capability': '8.0'
    },
    {
        'id': 'gpu-server-2-gpu-4',
        'name': 'GPU Server 2 - GPU 4',
        'host': '192.168.1.102',
        'port': 5005,
        'gpu_device_id': 4,
        'gpu_model': 'A100',
        'gpu_memory': '80GB',
        'compute_capability': '8.0'
    },
    {
        'id': 'gpu-server-2-gpu-5',
        'name': 'GPU Server 2 - GPU 5',
        'host': '192.168.1.102',
        'port': 5006,
        'gpu_device_id': 5,
        'gpu_model': 'A100',
        'gpu_memory': '80GB',
        'compute_capability': '8.0'
    },
    {
        'id': 'gpu-server-2-gpu-6',
        'name': 'GPU Server 2 - GPU 6',
        'host': '192.168.1.102',
        'port': 5007,
        'gpu_device_id': 6,
        'gpu_model': 'A100',
        'gpu_memory': '80GB',
        'compute_capability': '8.0'
    },
    {
        'id': 'gpu-server-2-gpu-7',
        'name': 'GPU Server 2 - GPU 7',
        'host': '192.168.1.102',
        'port': 5008,
        'gpu_device_id': 7,
        'gpu_model': 'A100',
        'gpu_memory': '80GB',
        'compute_capability': '8.0'
    },
    
    # GPU机器3 (192.168.1.103) - 8张H100
    {
        'id': 'gpu-server-3-gpu-0',
        'name': 'GPU Server 3 - GPU 0',
        'host': '192.168.1.103',
        'port': 5001,
        'gpu_device_id': 0,
        'gpu_model': 'H100',
        'gpu_memory': '80GB',
        'compute_capability': '9.0'
    },
    {
        'id': 'gpu-server-3-gpu-1',
        'name': 'GPU Server 3 - GPU 1',
        'host': '192.168.1.103',
        'port': 5002,
        'gpu_device_id': 1,
        'gpu_model': 'H100',
        'gpu_memory': '80GB',
        'compute_capability': '9.0'
    },
    {
        'id': 'gpu-server-3-gpu-2',
        'name': 'GPU Server 3 - GPU 2',
        'host': '192.168.1.103',
        'port': 5003,
        'gpu_device_id': 2,
        'gpu_model': 'H100',
        'gpu_memory': '80GB',
        'compute_capability': '9.0'
    },
    {
        'id': 'gpu-server-3-gpu-3',
        'name': 'GPU Server 3 - GPU 3',
        'host': '192.168.1.103',
        'port': 5004,
        'gpu_device_id': 3,
        'gpu_model': 'H100',
        'gpu_memory': '80GB',
        'compute_capability': '9.0'
    },
    {
        'id': 'gpu-server-3-gpu-4',
        'name': 'GPU Server 3 - GPU 4',
        'host': '192.168.1.103',
        'port': 5005,
        'gpu_device_id': 4,
        'gpu_model': 'H100',
        'gpu_memory': '80GB',
        'compute_capability': '9.0'
    },
    {
        'id': 'gpu-server-3-gpu-5',
        'name': 'GPU Server 3 - GPU 5',
        'host': '192.168.1.103',
        'port': 5006,
        'gpu_device_id': 5,
        'gpu_model': 'H100',
        'gpu_memory': '80GB',
        'compute_capability': '9.0'
    },
    {
        'id': 'gpu-server-3-gpu-6',
        'name': 'GPU Server 3 - GPU 6',
        'host': '192.168.1.103',
        'port': 5007,
        'gpu_device_id': 6,
        'gpu_model': 'H100',
        'gpu_memory': '80GB',
        'compute_capability': '9.0'
    },
    {
        'id': 'gpu-server-3-gpu-7',
        'name': 'GPU Server 3 - GPU 7',
        'host': '192.168.1.103',
        'port': 5008,
        'gpu_device_id': 7,
        'gpu_model': 'H100',
        'gpu_memory': '80GB',
        'compute_capability': '9.0'
    },
]

# 任务配置
TASK_TIMEOUT = 300
MAX_QUEUE_SIZE = 100

# GPU监控配置
GPU_MONITOR_INTERVAL = 2

# GPU资源限制
GPU_MEMORY_THRESHOLD = 90
GPU_UTILIZATION_THRESHOLD = 95

# ============================================================
# 使用说明
# ============================================================

"""
多GPU部署步骤:

1. 主节点 (192.168.1.100):
   - 安装Redis并配置允许远程连接
   - 使用本配置文件: cp config_multi_gpu.py config.py
   - 启动主节点: python3 app.py

2. GPU机器1 (192.168.1.101) - 4张GPU:
   ./start_multi_gpu_workers.sh
   
   或手动启动:
   python3 gpu_worker_mq.py --id gpu-server-1-gpu-0 --gpu 0 --redis-host 192.168.1.100 &
   python3 gpu_worker_mq.py --id gpu-server-1-gpu-1 --gpu 1 --redis-host 192.168.1.100 &
   python3 gpu_worker_mq.py --id gpu-server-1-gpu-2 --gpu 2 --redis-host 192.168.1.100 &
   python3 gpu_worker_mq.py --id gpu-server-1-gpu-3 --gpu 3 --redis-host 192.168.1.100 &

3. GPU机器2 (192.168.1.102) - 8张GPU:
   ./start_multi_gpu_workers.sh

4. GPU机器3 (192.168.1.103) - 8张GPU:
   ./start_multi_gpu_workers.sh

验证部署:
  - 查看Worker: redis-cli -h 192.168.1.100 KEYS 'leetgpu:workers:status:*'
  - 总Worker数: 4 + 8 + 8 = 20个Worker

详细文档: MULTI_GPU_SUPPORT.md
"""

if __name__ == "__main__":
    print("="*60)
    print("多GPU配置信息")
    print("="*60)
    print(f"主节点: {REDIS_HOST}:{REDIS_PORT}")
    print(f"\n配置的GPU Workers: {len(GPU_WORKERS)}个")
    
    # 统计每台机器的GPU数量
    servers = {}
    for worker in GPU_WORKERS:
        host = worker['host']
        if host not in servers:
            servers[host] = []
        servers[host].append(worker)
    
    print(f"\nGPU服务器: {len(servers)}台")
    for host, workers in servers.items():
        print(f"\n{host}:")
        print(f"  GPU数量: {len(workers)}")
        print(f"  GPU型号: {workers[0]['gpu_model']}")
        print(f"  Workers:")
        for w in workers:
            print(f"    - {w['id']} (GPU {w['gpu_device_id']})")
    
    print("\n" + "="*60)
    print("使用 start_multi_gpu_workers.sh 在GPU机器上启动Worker")
    print("="*60)
