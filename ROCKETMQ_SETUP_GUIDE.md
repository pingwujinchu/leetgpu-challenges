# RocketMQ 消息队列集成指南

本项目已集成 Apache RocketMQ 作为消息队列，用于主从节点之间的任务通信。

## 📋 目录

- [系统架构](#系统架构)
- [RocketMQ 安装](#rocketmq-安装)
- [配置说明](#配置说明)
- [启动服务](#启动服务)
- [使用示例](#使用示例)
- [测试](#测试)
- [常见问题](#常见问题)

## 🏗️ 系统架构

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   主节点    │────────>│   RocketMQ   │<────────│  GPU Worker │
│ (Producer)  │         │  NameServer  │         │ (Consumer)  │
└─────────────┘         └──────────────┘         └─────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
              ┌──────▼──────┐      ┌─────▼──────┐
              │   Broker    │      │   Broker   │
              │  (Master)   │      │  (Slave)   │
              └─────────────┘      └────────────┘
```

### 核心组件

1. **主节点 (Master/Producer)**
   - 推送任务到 RocketMQ
   - 接收 Worker 心跳和任务结果
   - 管理任务状态

2. **RocketMQ**
   - **NameServer**: 路由管理和服务发现
   - **Broker**: 消息存储和传输
   - **Topics**: 
     - `leetgpu_tasks`: 任务队列
     - `leetgpu_results`: 结果队列
     - `leetgpu_heartbeat`: Worker 心跳

3. **GPU Worker (Consumer)**
   - 订阅特定 GPU 型号的任务
   - 执行 CUDA 任务
   - 发送结果和心跳

## 📦 RocketMQ 安装

### 方式 1: Docker (推荐)

```bash
# 1. 拉取 RocketMQ 镜像
docker pull apache/rocketmq:5.1.4

# 2. 启动 NameServer
docker run -d \
  --name rmqnamesrv \
  -p 9876:9876 \
  apache/rocketmq:5.1.4 \
  sh mqnamesrv

# 3. 启动 Broker
docker run -d \
  --name rmqbroker \
  --link rmqnamesrv:namesrv \
  -p 10909:10909 \
  -p 10911:10911 \
  -e "NAMESRV_ADDR=namesrv:9876" \
  apache/rocketmq:5.1.4 \
  sh mqbroker -c /home/rocketmq/rocketmq-5.1.4/conf/broker.conf
```

### 方式 2: 本地安装

```bash
# 1. 下载 RocketMQ
wget https://archive.apache.org/dist/rocketmq/5.1.4/rocketmq-all-5.1.4-bin-release.zip
unzip rocketmq-all-5.1.4-bin-release.zip
cd rocketmq-5.1.4

# 2. 启动 NameServer
nohup sh bin/mqnamesrv &

# 3. 启动 Broker
nohup sh bin/mqbroker -n localhost:9876 &

# 4. 验证安装
sh bin/mqadmin clusterList -n localhost:9876
```

### 方式 3: Docker Compose (最简单)

创建 `docker-compose-rocketmq.yml`:

```yaml
version: '3.8'
services:
  namesrv:
    image: apache/rocketmq:5.1.4
    container_name: rmqnamesrv
    ports:
      - 9876:9876
    command: sh mqnamesrv
    networks:
      - rocketmq
    
  broker:
    image: apache/rocketmq:5.1.4
    container_name: rmqbroker
    ports:
      - 10909:10909
      - 10911:10911
    depends_on:
      - namesrv
    environment:
      - NAMESRV_ADDR=namesrv:9876
    command: sh mqbroker -c /home/rocketmq/rocketmq-5.1.4/conf/broker.conf
    networks:
      - rocketmq

networks:
  rocketmq:
    driver: bridge
```

启动:

```bash
docker-compose -f docker-compose-rocketmq.yml up -d
```

## ⚙️ 配置说明

### 1. 安装 Python 依赖

```bash
cd website
pip install -r requirements.txt
```

### 2. 配置文件 (`website/config.py`)

```python
# RocketMQ配置
ROCKETMQ_NAMESERVER = 'localhost:9876'
ROCKETMQ_GROUP_ID = 'leetgpu_group'
ROCKETMQ_TASK_TOPIC = 'leetgpu_tasks'
ROCKETMQ_RESULT_TOPIC = 'leetgpu_results'
ROCKETMQ_HEARTBEAT_TOPIC = 'leetgpu_heartbeat'

# 消息队列选择
MESSAGE_QUEUE_TYPE = 'rocketmq'  # 或 'redis'
```

### 3. GPU Worker 配置

在 `config.py` 中配置 Worker 节点:

```python
GPU_WORKERS = [
    {
        'id': 'gpu-worker-1',
        'name': 'GPU Worker 1',
        'gpu_model': 'RTX 4090',
        'gpu_memory': '24GB',
        'compute_capability': '8.9'
    },
    # ... 更多 Worker
]
```

## 🚀 启动服务

### 方式 1: 一键启动所有服务

```bash
cd website
./start_all_rocketmq.sh
```

这将启动:
- 主节点 (Flask Web 服务)
- GPU Worker 1 (RTX 4090)
- GPU Worker 2 (A100)
- GPU Worker 3 (H100)

### 方式 2: 分别启动

**启动主节点:**

```bash
cd website
python app.py --mode rocketmq
```

**启动 Worker:**

```bash
# Worker 1
./start_worker_rocketmq.sh gpu-worker-1 0 "RTX 4090" localhost:9876

# Worker 2
./start_worker_rocketmq.sh gpu-worker-2 0 "A100" localhost:9876

# Worker 3
./start_worker_rocketmq.sh gpu-worker-3 0 "H100" localhost:9876
```

### 方式 3: 手动启动

**主节点:**

```bash
python task_manager_rocketmq.py
```

**Worker:**

```bash
python gpu_worker_rocketmq.py \
    --id gpu-worker-1 \
    --gpu 0 \
    --gpu-model "RTX 4090" \
    --nameserver localhost:9876 \
    --group-id leetgpu_group
```

## 💡 使用示例

### Python API 示例

```python
from task_manager_rocketmq import TaskManagerRocketMQ
from config import GPU_WORKERS, ROCKETMQ_NAMESERVER, ROCKETMQ_GROUP_ID

# 创建任务管理器
manager = TaskManagerRocketMQ(
    GPU_WORKERS, 
    ROCKETMQ_NAMESERVER, 
    ROCKETMQ_GROUP_ID
)

# 启动监控
manager.start_monitor()

# 提交任务 (指定 GPU 型号)
task_id = manager.submit_task(
    code="""
def vector_add(a, b, c):
    idx = cuda.grid(1)
    if idx < c.size:
        c[idx] = a[idx] + b[idx]
""",
    inputs=[],
    grid_size=(32,),
    block_size=(32,),
    gpu_model="RTX 4090"  # 任务会路由到 RTX 4090 Worker
)

# 查询任务状态
status = manager.get_task_status(task_id)
print(f"任务状态: {status['status']}")

# 获取 Worker 状态
workers = manager.get_worker_status()
for w in workers:
    print(f"{w['name']}: {w['status']}")

# 关闭
manager.shutdown()
```

### REST API 示例

**提交任务:**

```bash
curl -X POST http://localhost:5000/api/submit \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def vector_add(a, b, c): ...",
    "inputs": [],
    "grid_size": [32],
    "block_size": [32],
    "gpu_model": "RTX 4090"
  }'
```

**查询任务状态:**

```bash
curl http://localhost:5000/api/status/<task_id>
```

**查询 Worker 状态:**

```bash
curl http://localhost:5000/api/workers
```

## 🧪 测试

### 运行测试套件

```bash
cd website
python test_rocketmq.py
```

测试包括:
- ✅ 基本操作测试 (推送/拉取/结果存储)
- ✅ GPU 型号路由测试
- ✅ 性能测试 (批量任务)

### 手动测试

```bash
# 测试消息队列
python message_queue_rocketmq.py

# 测试任务管理器
python task_manager_rocketmq.py

# 测试 Worker
python gpu_worker_rocketmq.py --id test-worker --gpu 0 --gpu-model "RTX 4090"
```

## 🔧 GPU 型号路由

RocketMQ 通过 **Tag** 机制实现 GPU 型号路由:

### 工作原理

1. **任务推送**: 主节点根据 `gpu_model` 设置 Tag
   ```python
   # gpu_model = "RTX 4090" -> Tag = "RTX_4090"
   # gpu_model = None -> Tag = "GENERAL"
   ```

2. **任务订阅**: Worker 订阅特定 GPU 型号的 Tag
   ```python
   # Worker 1 订阅: "RTX_4090"
   # Worker 2 订阅: "A100"
   # Worker 3 订阅: "*" (所有任务)
   ```

### 示例

```python
# 推送到 RTX 4090 队列
manager.submit_task(code, inputs, grid_size, block_size, gpu_model="RTX 4090")

# 推送到通用队列 (所有 Worker 都能接收)
manager.submit_task(code, inputs, grid_size, block_size, gpu_model=None)
```

## 🐛 常见问题

### 1. 连接 RocketMQ 失败

**问题**: `⚠️ 消息队列连接失败`

**解决**:
```bash
# 检查 RocketMQ 是否运行
docker ps | grep rocketmq

# 检查端口
netstat -an | grep 9876

# 重启 RocketMQ
docker restart rmqnamesrv rmqbroker
```

### 2. Worker 收不到任务

**问题**: Worker 启动但无任务

**解决**:
1. 检查 GPU 型号配置是否匹配
2. 查看 Worker 日志是否有错误
3. 验证 Topic 是否正确创建:
   ```bash
   docker exec rmqbroker sh mqadmin topicList -n localhost:9876
   ```

### 3. 任务结果丢失

**问题**: 任务执行完成但查询不到结果

**解决**:
- 结果有 TTL (默认 1 小时)
- 检查结果 Consumer 是否正常运行
- 查看 `leetgpu_results` Topic 的消息

### 4. 性能问题

**优化建议**:
- 增加 Broker 数量实现负载均衡
- 调整 Consumer 线程数
- 启用批量发送:
  ```python
  producer.set_max_message_size(4096)
  ```

### 5. 内存模式运行

如果 RocketMQ 不可用，系统会自动降级到内存模式:

```
⚠️ RocketMQ客户端未安装，使用模拟模式（内存队列）
```

内存模式仅用于开发测试，不支持分布式部署。

## 📊 监控和管理

### RocketMQ Console

安装 RocketMQ Console 进行可视化管理:

```bash
docker run -d \
  --name rocketmq-console \
  -e "JAVA_OPTS=-Drocketmq.namesrv.addr=rmqnamesrv:9876" \
  -p 8080:8080 \
  --link rmqnamesrv:rmqnamesrv \
  apacherocketmq/rocketmq-console:2.0.0
```

访问: http://localhost:8080

### 查看 Topic 信息

```bash
# 列出所有 Topic
docker exec rmqbroker sh mqadmin topicList -n localhost:9876

# 查看 Topic 统计
docker exec rmqbroker sh mqadmin topicStatus -n localhost:9876 -t leetgpu_tasks
```

### 查看消费者组

```bash
# 消费者组列表
docker exec rmqbroker sh mqadmin consumerProgress -n localhost:9876
```

## 🔄 从 Redis 迁移

如果你之前使用 Redis，迁移到 RocketMQ 很简单:

1. **修改配置**:
   ```python
   MESSAGE_QUEUE_TYPE = 'rocketmq'  # 改为 rocketmq
   ```

2. **启动 RocketMQ**:
   ```bash
   docker-compose -f docker-compose-rocketmq.yml up -d
   ```

3. **重启服务**:
   ```bash
   ./start_all_rocketmq.sh
   ```

代码无需修改，接口完全兼容!

## 📚 更多资源

- [RocketMQ 官方文档](https://rocketmq.apache.org/)
- [RocketMQ Python Client](https://github.com/apache/rocketmq-client-python)
- [项目 README](README.md)
- [快速开始指南](QUICK_START_MQ.md)

## 🆘 获取帮助

遇到问题?
1. 查看日志输出
2. 运行测试套件: `python test_rocketmq.py`
3. 检查 RocketMQ 状态
4. 提交 Issue

---

**祝使用愉快! 🚀**
