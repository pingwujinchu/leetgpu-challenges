"""
分布式部署配置示例
主节点和GPU Worker部署在不同机器上
"""

# ============================================================
# 主节点配置
# ============================================================

# 主节点监听配置
MASTER_HOST = '0.0.0.0'  # 监听所有网络接口
MASTER_PORT = 5000

# ============================================================
# Redis配置（部署在主节点上）
# ============================================================

# Redis服务器地址（主节点IP）
REDIS_HOST = '192.168.1.100'  # 🔧 修改为主节点的实际IP
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None  # 生产环境建议设置密码

# ============================================================
# GPU Worker节点配置
# ============================================================

# 配置所有GPU机器的信息
GPU_WORKERS = [
    {
        'id': 'gpu-worker-1',
        'name': 'GPU Server 1 - RTX 4090',
        'host': '192.168.1.101',  # 🔧 GPU机器1的IP地址
        'port': 5001,  # Worker HTTP端口（消息队列模式可忽略）
        'gpu_model': 'RTX 4090',
        'gpu_memory': '24GB',
        'compute_capability': '8.9'
    },
    {
        'id': 'gpu-worker-2',
        'name': 'GPU Server 2 - A100',
        'host': '192.168.1.102',  # 🔧 GPU机器2的IP地址
        'port': 5002,
        'gpu_model': 'A100',
        'gpu_memory': '40GB',
        'compute_capability': '8.0'
    },
    {
        'id': 'gpu-worker-3',
        'name': 'GPU Server 3 - H100',
        'host': '192.168.1.103',  # 🔧 GPU机器3的IP地址
        'port': 5003,
        'gpu_model': 'H100',
        'gpu_memory': '80GB',
        'compute_capability': '9.0'
    }
]

# ============================================================
# 任务配置
# ============================================================

TASK_TIMEOUT = 300  # 任务超时时间（秒）
MAX_QUEUE_SIZE = 100  # 最大队列大小

# ============================================================
# GPU监控配置
# ============================================================

GPU_MONITOR_INTERVAL = 2  # GPU监控间隔（秒）

# ============================================================
# GPU资源限制配置
# ============================================================

GPU_MEMORY_THRESHOLD = 90  # 显存利用率阈值（%）
GPU_UTILIZATION_THRESHOLD = 95  # GPU利用率阈值（%）

# ============================================================
# 网络配置
# ============================================================

# 连接超时（秒）
NETWORK_TIMEOUT = 10

# 心跳间隔（秒）
HEARTBEAT_INTERVAL = 5

# Worker离线超时（秒）
WORKER_OFFLINE_TIMEOUT = 30

# ============================================================
# 安全配置
# ============================================================

# 是否启用认证（未实现，预留）
ENABLE_AUTH = False

# API密钥（未实现，预留）
API_KEY = None

# 允许的IP白名单（未实现，预留）
ALLOWED_IPS = [
    '192.168.1.100',  # 主节点
    '192.168.1.101',  # GPU机器1
    '192.168.1.102',  # GPU机器2
    '192.168.1.103',  # GPU机器3
]

# ============================================================
# 部署说明
# ============================================================

"""
分布式部署步骤:

1. 主节点机器 (192.168.1.100):
   - 安装Redis: sudo apt-get install redis-server
   - 配置Redis允许远程: bind 0.0.0.0
   - 重启Redis: sudo systemctl restart redis
   - 开放端口: sudo ufw allow 6379,5000/tcp
   - 启动Flask: python3 app.py

2. GPU Worker机器 (192.168.1.101-103):
   - 安装依赖: pip install -r requirements.txt
   - 复制配置: scp master:/path/to/config_distributed.py ./config.py
   - 启动Worker: 
     python3 gpu_worker_mq.py --id gpu-worker-X --gpu 0 \
         --redis-host 192.168.1.100

3. 验证部署:
   - Redis连接: redis-cli -h 192.168.1.100 ping
   - Worker状态: redis-cli -h 192.168.1.100 KEYS 'leetgpu:workers:*'
   - 提交任务测试

详细文档: DISTRIBUTED_DEPLOYMENT.md
"""

# ============================================================
# 环境检测
# ============================================================

import socket

def get_local_ip():
    """获取本机IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# 自动检测本机IP（仅供参考）
LOCAL_IP = get_local_ip()

if __name__ == "__main__":
    print("="*60)
    print("LeetGPU 分布式配置信息")
    print("="*60)
    print(f"本机IP: {LOCAL_IP}")
    print(f"主节点: {MASTER_HOST}:{MASTER_PORT}")
    print(f"Redis服务器: {REDIS_HOST}:{REDIS_PORT}")
    print(f"\nGPU Worker配置:")
    for worker in GPU_WORKERS:
        print(f"  - {worker['name']}")
        print(f"    IP: {worker['host']}")
        print(f"    GPU: {worker['gpu_model']} ({worker['gpu_memory']})")
    print("="*60)
    print("\n提示:")
    print("1. 修改REDIS_HOST为主节点实际IP")
    print("2. 修改GPU_WORKERS中的host为GPU机器实际IP")
    print("3. 确保网络互通和防火墙开放")
    print("4. 查看详细部署文档: DISTRIBUTED_DEPLOYMENT.md")
    print("="*60)
