# 分布式部署指南

## 🌐 部署架构

主节点和从节点部署在不同机器上，通过网络连接。

```
┌─────────────────────────┐
│   主节点机器 (CPU)       │
│   IP: 192.168.1.100     │
│                         │
│   • Flask Web (5000)   │
│   • TaskManager        │
│   • Redis (6379)       │
└──────────┬──────────────┘
           │
       (网络通信)
           │
    ┌──────┴──────┬──────────────┐
    │             │              │
┌───▼────┐  ┌────▼───┐  ┌───────▼──┐
│GPU机器1│  │GPU机器2│  │ GPU机器3 │
│IP: .101│  │IP: .102│  │ IP: .103 │
│        │  │        │  │          │
│Worker 1│  │Worker 2│  │ Worker 3 │
│RTX 4090│  │A100    │  │ H100     │
└────────┘  └────────┘  └──────────┘
```

## 📋 部署清单

### 主节点机器（CPU服务器）
- ✅ Python 3.8+
- ✅ Redis服务器
- ✅ Flask Web应用
- ✅ 对外网络访问

### GPU Worker机器（GPU服务器）
- ✅ Python 3.8+
- ✅ NVIDIA GPU + CUDA
- ✅ Numba（CUDA JIT支持）
- ✅ 能访问主节点Redis

## 🔧 配置步骤

### 1. 主节点配置

**编辑 `config.py`**:

```python
# 主节点配置
MASTER_HOST = '0.0.0.0'  # 监听所有网络接口
MASTER_PORT = 5000

# Redis配置（主节点上）
REDIS_HOST = '0.0.0.0'  # 允许远程连接
REDIS_PORT = 6379
REDIS_DB = 0

# GPU Worker节点配置（修改为实际IP）
GPU_WORKERS = [
    {
        'id': 'gpu-worker-1',
        'name': 'GPU Server 1',
        'host': '192.168.1.101',  # GPU机器1的IP
        'port': 5001,
        'gpu_model': 'RTX 4090',
        'gpu_memory': '24GB',
        'compute_capability': '8.9'
    },
    {
        'id': 'gpu-worker-2',
        'name': 'GPU Server 2',
        'host': '192.168.1.102',  # GPU机器2的IP
        'port': 5002,
        'gpu_model': 'A100',
        'gpu_memory': '40GB',
        'compute_capability': '8.0'
    },
    {
        'id': 'gpu-worker-3',
        'name': 'GPU Server 3',
        'host': '192.168.1.103',  # GPU机器3的IP
        'port': 5003,
        'gpu_model': 'H100',
        'gpu_memory': '80GB',
        'compute_capability': '9.0'
    }
]
```

### 2. Redis配置（主节点）

**编辑 `/etc/redis/redis.conf`**:

```bash
# 允许远程连接（注释掉bind 127.0.0.1）
bind 0.0.0.0

# 设置密码（推荐）
requirepass your_strong_password_here

# 关闭保护模式
protected-mode no

# 持久化
save 900 1
save 300 10
save 60 10000
```

**重启Redis**:
```bash
sudo systemctl restart redis
```

### 3. 防火墙配置

**主节点**:
```bash
# 开放Redis端口（6379）
sudo ufw allow 6379/tcp

# 开放Web端口（5000）
sudo ufw allow 5000/tcp

# 或使用iptables
sudo iptables -A INPUT -p tcp --dport 6379 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
```

**GPU Worker机器**（如果需要HTTP模式）:
```bash
# 开放Worker端口（5001-5003）
sudo ufw allow 5001:5003/tcp
```

### 4. 网络连通性测试

**从GPU机器测试连接主节点Redis**:
```bash
# 测试Redis连接
redis-cli -h 192.168.1.100 -p 6379 -a your_password ping
# 应返回: PONG

# 测试网络连通性
ping 192.168.1.100
telnet 192.168.1.100 6379
```

## 🚀 部署步骤

### 在主节点机器上

```bash
# 1. 安装依赖
cd /workspace/website
pip install -r requirements.txt

# 2. 配置Redis（见上面Redis配置）
sudo vim /etc/redis/redis.conf
sudo systemctl restart redis

# 3. 验证Redis
redis-cli -h 0.0.0.0 ping

# 4. 启动主节点服务
python3 app.py
# 或使用消息队列模式的任务管理器
```

### 在每台GPU机器上

```bash
# 1. 克隆代码或复制必要文件
scp user@192.168.1.100:/path/to/website/*.py .
scp user@192.168.1.100:/path/to/website/config.py .

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动Worker（消息队列模式）
python3 gpu_worker_mq.py \
    --id gpu-worker-1 \
    --gpu 0 \
    --redis-host 192.168.1.100 \
    --redis-port 6379

# 如果Redis有密码，需要修改message_queue.py支持密码
```

### 使用启动脚本

**GPU机器1** (192.168.1.101):
```bash
./start_worker_mq.sh \
    --id gpu-worker-1 \
    --gpu 0 \
    --redis-host 192.168.1.100 \
    --redis-port 6379
```

**GPU机器2** (192.168.1.102):
```bash
./start_worker_mq.sh \
    --id gpu-worker-2 \
    --gpu 0 \
    --redis-host 192.168.1.100 \
    --redis-port 6379
```

**GPU机器3** (192.168.1.103):
```bash
./start_worker_mq.sh \
    --id gpu-worker-3 \
    --gpu 0 \
    --redis-host 192.168.1.100 \
    --redis-port 6379
```

## 🔐 安全配置

### 1. Redis密码认证

**修改 `message_queue.py`** 支持密码:

```python
def __init__(self, host: str = 'localhost', port: int = 6379, 
             db: int = 0, password: str = None):
    self.redis_client = redis.Redis(
        host=host,
        port=port,
        db=db,
        password=password,  # 添加密码参数
        decode_responses=True
    )
```

**使用时传入密码**:
```python
from message_queue import MessageQueue
mq = MessageQueue(
    host='192.168.1.100',
    port=6379,
    password='your_password'
)
```

### 2. SSL/TLS加密

**Redis SSL配置** (redis.conf):
```bash
tls-port 6380
tls-cert-file /path/to/redis.crt
tls-key-file /path/to/redis.key
tls-ca-cert-file /path/to/ca.crt
```

### 3. IP白名单

**Redis配置**:
```bash
# 只允许特定IP访问
bind 192.168.1.100 192.168.1.101 192.168.1.102 192.168.1.103
```

### 4. 防火墙规则

```bash
# 只允许GPU机器访问Redis
sudo ufw allow from 192.168.1.101 to any port 6379
sudo ufw allow from 192.168.1.102 to any port 6379
sudo ufw allow from 192.168.1.103 to any port 6379
sudo ufw deny 6379
```

## 🔍 监控和验证

### 检查Worker连接

**在主节点上**:
```bash
# 查看所有Worker状态
redis-cli KEYS 'leetgpu:workers:status:*'

# 查看特定Worker
redis-cli GET leetgpu:workers:status:gpu-worker-1
redis-cli GET leetgpu:workers:status:gpu-worker-2
redis-cli GET leetgpu:workers:status:gpu-worker-3
```

### 查看网络连接

```bash
# 主节点查看Redis连接
netstat -an | grep 6379

# 应该看到来自GPU机器的连接
tcp  0  0  192.168.1.100:6379  192.168.1.101:xxxxx  ESTABLISHED
tcp  0  0  192.168.1.100:6379  192.168.1.102:xxxxx  ESTABLISHED
tcp  0  0  192.168.1.100:6379  192.168.1.103:xxxxx  ESTABLISHED
```

### 测试任务分发

```python
# 在主节点执行
from task_manager_mq import TaskManagerMQ
from config import GPU_WORKERS, REDIS_HOST, REDIS_PORT, REDIS_DB

manager = TaskManagerMQ(GPU_WORKERS, REDIS_HOST, REDIS_PORT, REDIS_DB)
manager.start_monitor()

# 提交测试任务
task_id = manager.submit_task(
    code='def test(): pass',
    inputs=[],
    grid_size=(1,),
    block_size=(1,)
)

print(f"任务ID: {task_id}")

# 查看Worker状态
workers = manager.get_worker_status()
for w in workers:
    print(f"{w['name']}: {'在线' if w['online'] else '离线'}")
```

## 🐛 常见问题

### 问题1: Worker连接不上Redis

**检查清单**:
```bash
# 1. Redis是否监听0.0.0.0
netstat -an | grep 6379

# 2. 防火墙是否开放
sudo ufw status

# 3. 网络是否连通
ping 192.168.1.100

# 4. Redis是否需要密码
redis-cli -h 192.168.1.100 ping
# 如果返回 (error) NOAUTH，说明需要密码
redis-cli -h 192.168.1.100 -a password ping
```

### 问题2: Worker在线但不拉取任务

**检查**:
```bash
# GPU机器上查看Worker日志
tail -f logs/worker1_mq.log

# 主节点查看队列
redis-cli LLEN leetgpu:tasks:queue

# 查看Worker状态
redis-cli GET leetgpu:workers:status:gpu-worker-1
```

### 问题3: 任务结果查询不到

**可能原因**:
- Redis TTL过期（默认1小时）
- 网络延迟
- Worker未成功保存结果

**调试**:
```bash
# 查看所有结果键
redis-cli KEYS 'leetgpu:results:*'

# 查看特定结果
redis-cli GET leetgpu:results:{task_id}
```

## 📊 性能优化

### 1. Redis性能调优

```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
tcp-backlog 511
timeout 0
tcp-keepalive 300
```

### 2. 网络优化

```bash
# 增加TCP缓冲区
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.wmem_max=16777216
```

### 3. 使用Redis Cluster（大规模）

对于大规模部署，考虑使用Redis Cluster：
```bash
# 主节点1
redis-server --port 6379 --cluster-enabled yes

# 主节点2
redis-server --port 6380 --cluster-enabled yes

# 创建集群
redis-cli --cluster create \
    192.168.1.100:6379 \
    192.168.1.100:6380 \
    --cluster-replicas 1
```

## 📋 部署检查清单

### 主节点部署

- [ ] Redis已安装并配置
- [ ] Redis监听0.0.0.0
- [ ] 防火墙已开放6379和5000端口
- [ ] config.py中IP配置正确
- [ ] 依赖已安装
- [ ] Flask应用正常启动

### GPU Worker部署

- [ ] 每台机器有GPU
- [ ] CUDA环境已配置
- [ ] Python依赖已安装
- [ ] 能连接主节点Redis
- [ ] config.py已同步
- [ ] Worker正常启动

### 网络检查

- [ ] 主节点<->Worker网络连通
- [ ] Redis连接测试通过
- [ ] 防火墙规则配置
- [ ] 心跳正常（redis-cli查看）
- [ ] 任务能正常分发

## 🎯 最佳实践

1. **使用域名**: 而不是硬编码IP
2. **配置监控**: Prometheus + Grafana
3. **日志集中**: ELK或Loki
4. **自动化部署**: Ansible/Docker
5. **备份Redis**: 定期备份数据
6. **负载均衡**: Nginx for Flask
7. **高可用**: Redis Sentinel

## 📝 配置文件示例

### 生产环境配置

```python
# config_production.py

# 主节点（使用域名）
MASTER_HOST = '0.0.0.0'
MASTER_PORT = 5000

# Redis（主节点）
REDIS_HOST = 'redis.internal.company.com'  # 使用域名
REDIS_PORT = 6379
REDIS_PASSWORD = 'your_secure_password'  # 生产环境密码
REDIS_DB = 0

# GPU Workers（使用域名或内网IP）
GPU_WORKERS = [
    {
        'id': 'gpu-server-1',
        'name': 'GPU Production Server 1',
        'host': 'gpu1.internal.company.com',  # 域名
        'port': 5001,
        'gpu_model': 'RTX 4090',
        'gpu_memory': '24GB',
        'compute_capability': '8.9'
    },
    {
        'id': 'gpu-server-2',
        'name': 'GPU Production Server 2',
        'host': 'gpu2.internal.company.com',
        'port': 5002,
        'gpu_model': 'A100',
        'gpu_memory': '80GB',
        'compute_capability': '8.0'
    }
]

# 资源限制
GPU_MEMORY_THRESHOLD = 85  # 生产环境更保守
GPU_UTILIZATION_THRESHOLD = 90
TASK_TIMEOUT = 600  # 10分钟
```

## 🚀 快速部署命令

```bash
# === 主节点 ===
# 1. 配置Redis
sudo sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf
sudo systemctl restart redis

# 2. 启动服务
cd /workspace/website
python3 app.py

# === GPU机器（每台执行）===
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动Worker
python3 gpu_worker_mq.py \
    --id gpu-worker-1 \
    --gpu 0 \
    --redis-host 192.168.1.100 \
    --redis-port 6379
```

---

**部署模式**: 分布式  
**通信方式**: Redis消息队列  
**适用场景**: 生产环境  
**维护成本**: 中等

🌐 **跨机器部署配置完成！**
