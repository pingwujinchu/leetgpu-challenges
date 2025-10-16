# 多GPU支持配置

## 🎯 场景说明

一台GPU服务器通常配备多张GPU卡，例如：
- GPU机器1: 4张RTX 4090
- GPU机器2: 8张A100
- GPU机器3: 8张H100

每张GPU卡可以运行一个Worker进程。

## 🏗️ 架构设计

```
主节点 (192.168.1.100)
  └── Redis + TaskManager
       ↓
  ┌────┴────┬─────────┐
  │         │         │
GPU机器1    GPU机器2   GPU机器3
(.101)      (.102)     (.103)
│           │          │
├─Worker1-0 ├─Worker2-0 ├─Worker3-0
│  GPU:0    │  GPU:0    │  GPU:0
│           │           │
├─Worker1-1 ├─Worker2-1 ├─Worker3-1
│  GPU:1    │  GPU:1    │  GPU:1
│           │           │
├─Worker1-2 ├─Worker2-2 ├─Worker3-2
│  GPU:2    │  GPU:2    │  GPU:2
│           │           │
└─Worker1-3 └─Worker2-3 └─Worker3-3
   GPU:3       GPU:3       GPU:3
```

## 🔧 配置方法

### 方式1: 修改config.py（推荐）

```python
# config_multi_gpu.py

GPU_WORKERS = [
    # GPU机器1 (192.168.1.101) - 4张RTX 4090
    {
        'id': 'gpu-server-1-gpu-0',
        'name': 'GPU Server 1 - GPU 0',
        'host': '192.168.1.101',
        'port': 5001,
        'gpu_device_id': 0,  # GPU设备ID
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
    # ... 继续添加GPU 2-7
    
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
    # ... 继续添加GPU 1-7
]
```

### 方式2: 启动脚本

**GPU机器1** (192.168.1.101 - 4张GPU):
```bash
# 启动4个Worker进程，每个绑定一张GPU
python3 gpu_worker_mq.py --id gpu-server-1-gpu-0 --gpu 0 --redis-host 192.168.1.100 &
python3 gpu_worker_mq.py --id gpu-server-1-gpu-1 --gpu 1 --redis-host 192.168.1.100 &
python3 gpu_worker_mq.py --id gpu-server-1-gpu-2 --gpu 2 --redis-host 192.168.1.100 &
python3 gpu_worker_mq.py --id gpu-server-1-gpu-3 --gpu 3 --redis-host 192.168.1.100 &
```

**GPU机器2** (192.168.1.102 - 8张GPU):
```bash
# 启动8个Worker进程
for i in {0..7}; do
    python3 gpu_worker_mq.py \
        --id gpu-server-2-gpu-$i \
        --gpu $i \
        --redis-host 192.168.1.100 &
done
```

**GPU机器3** (192.168.1.103 - 8张GPU):
```bash
# 启动8个Worker进程
for i in {0..7}; do
    python3 gpu_worker_mq.py \
        --id gpu-server-3-gpu-$i \
        --gpu $i \
        --redis-host 192.168.1.100 &
done
```

## 📝 自动启动脚本

### 创建启动脚本

**start_multi_gpu_workers.sh**:
```bash
#!/bin/bash
# 在GPU服务器上启动多个Worker

# 配置
REDIS_HOST="192.168.1.100"
SERVER_NAME=$(hostname)
NUM_GPUS=$(nvidia-smi --list-gpus | wc -l)

echo "======================================"
echo "启动多GPU Worker"
echo "======================================"
echo "服务器: $SERVER_NAME"
echo "GPU数量: $NUM_GPUS"
echo "Redis: $REDIS_HOST"
echo "======================================"
echo ""

# 启动每个GPU的Worker
for gpu_id in $(seq 0 $((NUM_GPUS-1))); do
    worker_id="$SERVER_NAME-gpu-$gpu_id"
    
    echo "启动 Worker: $worker_id (GPU $gpu_id)"
    
    python3 gpu_worker_mq.py \
        --id "$worker_id" \
        --gpu $gpu_id \
        --redis-host $REDIS_HOST \
        > logs/worker-$worker_id.log 2>&1 &
    
    echo "  PID: $!"
    sleep 1
done

echo ""
echo "======================================"
echo "所有Worker已启动"
echo "======================================"
echo ""
echo "查看日志:"
echo "  tail -f logs/worker-*.log"
echo ""
echo "查看进程:"
echo "  ps aux | grep gpu_worker_mq"
echo ""
```

### 使用方法

```bash
# 在每台GPU服务器上执行
chmod +x start_multi_gpu_workers.sh
./start_multi_gpu_workers.sh
```

## 🔍 GPU设备查询

### 查看GPU信息

```bash
# 查看所有GPU
nvidia-smi

# 查看GPU数量
nvidia-smi --list-gpus

# 查看特定GPU
nvidia-smi -i 0

# 查看GPU UUID
nvidia-smi -L
```

### 设置CUDA可见设备

```bash
# 方式1: 环境变量
export CUDA_VISIBLE_DEVICES=0  # 只使用GPU 0

# 方式2: 在代码中设置
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
```

## 📊 资源分配策略

### 策略1: 均匀分配

所有GPU平等对待，Worker自动竞争任务。

```
GPU 0: ████████░░ 80%
GPU 1: ███████░░░ 70%
GPU 2: █████████░ 90%
GPU 3: ██████░░░░ 60%

任务自动分配到GPU 3（负载最低）
```

### 策略2: 优先级分配

可以在config.py中设置优先级：

```python
{
    'id': 'gpu-server-1-gpu-0',
    'priority': 10,  # 高优先级
    ...
}
{
    'id': 'gpu-server-1-gpu-3',
    'priority': 1,   # 低优先级
    ...
}
```

### 策略3: 专用分配

某些GPU专门处理特定类型任务：

```python
{
    'id': 'gpu-server-1-gpu-0',
    'task_types': ['inference'],  # 只做推理
    ...
}
{
    'id': 'gpu-server-1-gpu-1',
    'task_types': ['training'],   # 只做训练
    ...
}
```

## 🔧 进程管理

### 使用systemd管理

**创建服务文件** `/etc/systemd/system/gpu-worker@.service`:

```ini
[Unit]
Description=GPU Worker %i
After=network.target

[Service]
Type=simple
User=gpu-user
WorkingDirectory=/workspace/website
ExecStart=/usr/bin/python3 gpu_worker_mq.py \
    --id gpu-server-1-gpu-%i \
    --gpu %i \
    --redis-host 192.168.1.100
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**使用方法**:
```bash
# 启动GPU 0的Worker
sudo systemctl start gpu-worker@0

# 启动所有GPU
for i in {0..7}; do
    sudo systemctl enable gpu-worker@$i
    sudo systemctl start gpu-worker@$i
done

# 查看状态
sudo systemctl status gpu-worker@*
```

### 使用supervisor管理

**supervisor配置** `/etc/supervisor/conf.d/gpu-workers.conf`:

```ini
[program:gpu-worker-0]
command=python3 gpu_worker_mq.py --id gpu-0 --gpu 0 --redis-host 192.168.1.100
directory=/workspace/website
autostart=true
autorestart=true
user=gpu-user

[program:gpu-worker-1]
command=python3 gpu_worker_mq.py --id gpu-1 --gpu 1 --redis-host 192.168.1.100
directory=/workspace/website
autostart=true
autorestart=true
user=gpu-user

; 继续添加更多GPU...
```

## 📈 监控多GPU

### 查看所有Worker状态

```bash
# Redis中查看所有Worker
redis-cli -h 192.168.1.100 KEYS 'leetgpu:workers:status:*'

# 查看特定机器的Workers
redis-cli -h 192.168.1.100 KEYS 'leetgpu:workers:status:gpu-server-1-*'
```

### GPU使用率监控

```bash
# 实时监控所有GPU
watch -n 1 nvidia-smi

# 查看GPU进程
nvidia-smi pmon

# 查看GPU拓扑
nvidia-smi topo -m
```

### 创建监控脚本

**monitor_gpus.sh**:
```bash
#!/bin/bash
# 监控本机所有GPU的Worker状态

REDIS_HOST="192.168.1.100"
SERVER_NAME=$(hostname)

while true; do
    clear
    echo "======================================"
    echo "GPU Worker 监控 - $SERVER_NAME"
    echo "======================================"
    date
    echo ""
    
    # 显示GPU状态
    nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu \
        --format=csv,noheader,nounits | \
    while IFS=',' read -r idx name util mem_used mem_total temp; do
        worker_id="$SERVER_NAME-gpu-$idx"
        
        # 从Redis获取Worker状态
        status=$(redis-cli -h $REDIS_HOST GET "leetgpu:workers:status:$worker_id" 2>/dev/null)
        
        echo "GPU $idx: $name"
        echo "  利用率: $util%"
        echo "  显存: ${mem_used}MB / ${mem_total}MB"
        echo "  温度: ${temp}°C"
        
        if [ -n "$status" ]; then
            echo "  Worker: 在线 ✓"
        else
            echo "  Worker: 离线 ✗"
        fi
        echo ""
    done
    
    sleep 5
done
```

## 💡 最佳实践

### 1. 资源隔离

每个Worker进程绑定到特定GPU：
```bash
# 使用CUDA_VISIBLE_DEVICES确保隔离
CUDA_VISIBLE_DEVICES=0 python3 gpu_worker_mq.py --id worker-0 --gpu 0 &
CUDA_VISIBLE_DEVICES=1 python3 gpu_worker_mq.py --id worker-1 --gpu 1 &
```

### 2. 内存限制

为每个Worker设置显存限制：
```python
# 在gpu_worker_mq.py中添加
import torch
torch.cuda.set_per_process_memory_fraction(0.9, device=gpu_id)
```

### 3. CPU亲和性

绑定Worker进程到特定CPU核心：
```bash
# 使用taskset绑定CPU
taskset -c 0-7 python3 gpu_worker_mq.py --id worker-0 --gpu 0 &
taskset -c 8-15 python3 gpu_worker_mq.py --id worker-1 --gpu 1 &
```

### 4. NUMA优化

对于多路CPU系统，绑定到对应NUMA节点：
```bash
# GPU 0-3 绑定到 NUMA 0
numactl --cpunodebind=0 --membind=0 python3 gpu_worker_mq.py --id worker-0 --gpu 0 &

# GPU 4-7 绑定到 NUMA 1
numactl --cpunodebind=1 --membind=1 python3 gpu_worker_mq.py --id worker-4 --gpu 4 &
```

## 📊 性能考虑

### GPU间通信

如果任务需要多GPU协作：
- 使用NVLink连接的GPU通信更快
- 使用`nvidia-smi topo -m`查看GPU拓扑

### 内存带宽

- PCIe 4.0 x16: ~32GB/s
- PCIe 5.0 x16: ~64GB/s
- NVLink 3.0: ~600GB/s

### 建议配置

| GPU数量 | Worker进程数 | 推荐配置 |
|---------|-------------|---------|
| 1-2张 | 1-2个 | 简单配置 |
| 4张 | 4个 | 标准配置 |
| 8张 | 8个 | 高端配置 |
| 8+张 | 按需配置 | 企业级 |

## 🐛 故障排查

### 问题1: Worker无法使用指定GPU

```bash
# 检查GPU是否可用
nvidia-smi -i 0

# 检查CUDA设备
python3 -c "import torch; print(torch.cuda.device_count())"

# 检查进程占用
nvidia-smi pmon
```

### 问题2: GPU之间负载不均

- 检查Worker是否都在运行
- 查看任务分配策略
- 检查GPU资源阈值设置

### 问题3: 多Worker进程冲突

- 确保每个Worker使用不同的GPU ID
- 使用CUDA_VISIBLE_DEVICES隔离
- 检查端口是否冲突（HTTP模式）

## 📝 配置生成工具

**generate_multi_gpu_config.py**:
```python
#!/usr/bin/env python3
"""
生成多GPU配置文件
"""

def generate_config(servers):
    """
    Args:
        servers: [
            {'host': '192.168.1.101', 'gpus': 4, 'model': 'RTX 4090'},
            {'host': '192.168.1.102', 'gpus': 8, 'model': 'A100'},
        ]
    """
    workers = []
    
    for server in servers:
        host = server['host']
        num_gpus = server['gpus']
        model = server['model']
        server_name = f"gpu-server-{host.split('.')[-1]}"
        
        for gpu_id in range(num_gpus):
            worker = {
                'id': f'{server_name}-gpu-{gpu_id}',
                'name': f'{server_name.upper()} GPU {gpu_id}',
                'host': host,
                'port': 5001 + gpu_id,
                'gpu_device_id': gpu_id,
                'gpu_model': model,
                'gpu_memory': '24GB',  # 根据实际修改
                'compute_capability': '8.9'
            }
            workers.append(worker)
    
    return workers

if __name__ == '__main__':
    servers = [
        {'host': '192.168.1.101', 'gpus': 4, 'model': 'RTX 4090'},
        {'host': '192.168.1.102', 'gpus': 8, 'model': 'A100'},
        {'host': '192.168.1.103', 'gpus': 8, 'model': 'H100'},
    ]
    
    workers = generate_config(servers)
    
    print("GPU_WORKERS = [")
    for w in workers:
        print(f"    {w},")
    print("]")
```

---

**支持**: 多GPU配置  
**模式**: 一GPU一Worker  
**推荐**: 生产环境使用

🎉 **支持单机多GPU部署！**
