# 消息队列架构文档

## 🎯 架构概述

LeetGPU主从架构升级为**消息队列模式**，实现解耦的异步任务处理：

- **主节点**: 推送任务到消息队列
- **从节点**: 从消息队列拉取任务执行  
- **消息队列**: Redis作为中间层，解耦主从节点

## 🏗️ 架构对比

### 旧架构（HTTP直接通信）

```
主节点 ─HTTP POST─> Worker 1
      ├─HTTP POST─> Worker 2
      └─HTTP POST─> Worker 3
      
问题:
  ❌ 主节点需要维护Worker连接
  ❌ Worker故障影响任务分配
  ❌ 负载不均衡
  ❌ 扩展性差
```

### 新架构（消息队列）

```
主节点 ─PUSH─> [消息队列] <─PULL─ Worker 1
                   ↑          <─PULL─ Worker 2  
                   ↓          <─PULL─ Worker 3
                结果存储
                
优势:
  ✅ 解耦主从节点
  ✅ 自动负载均衡
  ✅ 高可用性
  ✅ 易于扩展
  ✅ 支持持久化
```

## 📐 详细架构图

```
┌────────────────────────────────────────────────────────────┐
│                      主节点 (Master)                        │
│              Flask Web + TaskManagerMQ                     │
│                                                            │
│  用户提交 → 创建任务 → PUSH到队列                         │
│              ↓                                             │
│           任务状态查询 ← 从Redis获取结果                   │
└──────────────────────────┬─────────────────────────────────┘
                           │
                      [Redis服务器]
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    任务队列          结果存储          Worker状态
(leetgpu:tasks)   (leetgpu:results)  (leetgpu:workers)
         │                 │                 │
         └─────────────────┴─────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼───────┐  ┌───────▼───────┐  ┌──────▼────────┐
│  Worker 1     │  │  Worker 2     │  │  Worker 3     │
│  RTX 4090     │  │  A100         │  │  H100         │
│               │  │               │  │               │
│  PULL任务     │  │  PULL任务     │  │  PULL任务     │
│  ↓            │  │  ↓            │  │  ↓            │
│  执行计算     │  │  执行计算     │  │  执行计算     │
│  ↓            │  │  ↓            │  │  ↓            │
│  PUSH结果     │  │  PUSH结果     │  │  PUSH结果     │
│  ↓            │  │  ↓            │  │  ↓            │
│  发送心跳     │  │  发送心跳     │  │  发送心跳     │
└───────────────┘  └───────────────┘  └───────────────┘
```

## 🔑 核心组件

### 1. 消息队列模块 (`message_queue.py`)

**功能**:
- Redis连接管理
- 任务队列操作（push/pull）
- 结果存储和查询
- Worker心跳管理
- 内存队列后备（Redis不可用时）

**主要方法**:
```python
# 推送任务
mq.push_task(task_data)

# 拉取任务（阻塞）
task = mq.pull_task(timeout=1)

# 保存结果
mq.set_task_result(task_id, result)

# 获取结果
result = mq.get_task_result(task_id)

# 更新Worker状态（心跳）
mq.update_worker_status(worker_id, status)
```

### 2. 任务管理器MQ (`task_manager_mq.py`)

**功能**:
- 接收用户提交的任务
- 推送任务到消息队列
- 监控任务结果
- 查询Worker状态

**工作流程**:
```
用户提交任务
    ↓
创建Task对象
    ↓
序列化任务数据
    ↓
PUSH到Redis队列
    ↓
后台监控线程检查结果
    ↓
更新任务状态
```

### 3. GPU Worker MQ (`gpu_worker_mq.py`)

**功能**:
- 从消息队列拉取任务
- 检查GPU资源（阈值）
- 执行CUDA JIT编译和运行
- 保存结果到消息队列
- 发送心跳

**工作流程**:
```
启动Worker
    ↓
检查GPU资源
    ↓
从队列PULL任务（阻塞）
    ↓
执行CUDA JIT
    ↓
PUSH结果到Redis
    ↓
发送心跳到Redis
    ↓
循环继续
```

## 📊 数据结构

### 任务数据（队列中）

```json
{
  "task_id": "uuid",
  "code": "def kernel(): ...",
  "inputs": [...],
  "grid_size": [32],
  "block_size": [32],
  "gpu_model": "RTX 4090",
  "created_at": "2025-10-16T..."
}
```

### 结果数据（Redis）

```json
{
  "task_id": "uuid",
  "worker_id": "gpu-worker-1",
  "status": "completed",
  "started_at": "2025-10-16T...",
  "completed_at": "2025-10-16T...",
  "result": [...],
  "error": null
}
```

### Worker状态（心跳）

```json
{
  "worker_id": "gpu-worker-1",
  "status": "available",
  "current_task": null,
  "gpu_utilization": 45.2,
  "memory_utilization": 60.1,
  "temperature": 65,
  "power_usage": 280.5,
  "timestamp": "2025-10-16T..."
}
```

## 🔄 任务执行流程

### 完整流程

```
1. 用户提交任务 (Web/API)
       ↓
2. TaskManagerMQ.submit_task()
   - 创建Task对象
   - 生成UUID
   - 序列化数据
       ↓
3. MessageQueue.push_task()
   - RPUSH到Redis队列
   - 返回成功/失败
       ↓
4. Worker循环（各Worker独立）
   - check_resources()
   - pull_task(timeout=1)
   - 阻塞等待任务
       ↓
5. 拉取到任务
   - 标记为busy
   - set_task_result(status='running')
       ↓
6. execute_task()
   - 验证代码
   - 编译CUDA JIT
   - 执行计算
       ↓
7. 保存结果
   - set_task_result(status='completed')
   - 标记为available
       ↓
8. 主节点查询
   - get_task_result(task_id)
   - 返回给用户
```

### 资源检查流程

```
Worker准备拉取任务
    ↓
check_resources()
    ↓
查询GPU状态
    ↓
显存 < 90% ?
    ↓ NO
等待5秒
    ↓ YES
GPU利用率 < 95% ?
    ↓ NO
等待5秒
    ↓ YES
pull_task()
    ↓
执行任务
```

## 🚀 使用方式

### 安装Redis

**选项1: 本地安装**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# 验证
redis-cli ping
# 应返回: PONG
```

**选项2: Docker**
```bash
docker run -d -p 6379:6379 redis:alpine
```

**选项3: 无Redis（内存模式）**
系统会自动降级到内存队列模式（无持久化）

### 启动系统

**方式1: 一键启动**
```bash
cd /workspace/website

# 启动所有Worker（后台）
./start_all_mq.sh

# 启动主节点（需要另外启动Flask应用）
python3 app_mq.py  # 或修改app.py使用MessageQueue
```

**方式2: 分别启动**
```bash
# Worker 1
./start_worker_mq.sh --id gpu-worker-1 --gpu 0

# Worker 2
./start_worker_mq.sh --id gpu-worker-2 --gpu 0

# Worker 3
./start_worker_mq.sh --id gpu-worker-3 --gpu 0
```

### 测试

```python
from message_queue import get_message_queue
from task_manager_mq import TaskManagerMQ
from config import GPU_WORKERS, REDIS_HOST, REDIS_PORT, REDIS_DB

# 创建任务管理器
manager = TaskManagerMQ(GPU_WORKERS, REDIS_HOST, REDIS_PORT, REDIS_DB)
manager.start_monitor()

# 提交任务
task_id = manager.submit_task(
    code='def kernel(): pass',
    inputs=[],
    grid_size=(1,),
    block_size=(1,)
)

# 查询状态
import time
time.sleep(2)
status = manager.get_task_status(task_id)
print(status)
```

## 📈 性能特点

### 优势

1. **解耦**: 主从节点完全独立
2. **负载均衡**: Worker自动竞争任务
3. **高可用**: Worker故障不影响系统
4. **可扩展**: 随时添加Worker
5. **持久化**: Redis保证任务不丢失
6. **资源保护**: Worker自主检查资源

### 性能指标

- **任务推送延迟**: < 10ms
- **任务拉取延迟**: 阻塞模式，< 50ms
- **结果查询延迟**: < 5ms
- **心跳间隔**: 5秒
- **监控间隔**: 2秒

## 🔍 监控和调试

### Redis监控命令

```bash
# 查看队列大小
redis-cli LLEN leetgpu:tasks:queue

# 查看所有Worker状态
redis-cli KEYS 'leetgpu:workers:status:*'

# 查看特定Worker状态
redis-cli GET leetgpu:workers:status:gpu-worker-1

# 查看任务结果
redis-cli GET leetgpu:results:{task_id}

# 清空队列（慎用）
redis-cli DEL leetgpu:tasks:queue
```

### Worker日志

```bash
# 查看Worker日志
tail -f logs/worker1_mq.log
tail -f logs/worker2_mq.log
tail -f logs/worker3_mq.log
```

### 健康检查

```python
# 检查消息队列
mq = get_message_queue()
print(f"健康: {mq.health_check()}")
print(f"队列大小: {mq.get_queue_size()}")

# 检查任务管理器
health = manager.health_check()
print(f"消息队列: {health['message_queue']}")
print(f"在线Worker: {health['workers_online']}")
```

## 🐛 故障排查

### 问题1: Redis连接失败

**现象**: 
```
⚠️  消息队列连接失败: Connection refused
   使用模拟模式（内存队列）
```

**解决**:
```bash
# 检查Redis是否运行
redis-cli ping

# 启动Redis
redis-server

# 或使用Docker
docker run -d -p 6379:6379 redis:alpine
```

### 问题2: Worker不拉取任务

**可能原因**:
- Worker未启动
- GPU资源超过阈值
- Redis连接问题

**调试**:
```bash
# 检查Worker进程
ps aux | grep gpu_worker_mq

# 查看Worker日志
tail -f logs/worker1_mq.log

# 检查GPU资源
# 日志中会显示资源检查结果
```

### 问题3: 任务一直排队

**检查**:
```bash
# 队列大小
redis-cli LLEN leetgpu:tasks:queue

# 有Worker在线吗？
redis-cli KEYS 'leetgpu:workers:status:*'

# Worker状态
redis-cli GET leetgpu:workers:status:gpu-worker-1
```

## 🔒 安全建议

1. **Redis安全**:
   - 设置密码: `requirepass yourpassword`
   - 绑定IP: `bind 127.0.0.1`
   - 关闭危险命令

2. **网络安全**:
   - Redis不对公网开放
   - 使用防火墙限制访问
   - 考虑使用SSL/TLS

3. **数据安全**:
   - 定期备份Redis
   - 设置合适的TTL
   - 清理过期数据

## 🎯 最佳实践

1. **Worker数量**: 根据GPU数量和任务类型调整
2. **队列监控**: 定期检查队列积压
3. **结果TTL**: 根据需求设置（默认1小时）
4. **心跳间隔**: 平衡实时性和性能（默认5秒）
5. **资源阈值**: 根据任务大小调整（默认90%）

## 📚 相关文档

- 消息队列API: `message_queue.py`
- 任务管理器: `task_manager_mq.py`
- GPU Worker: `gpu_worker_mq.py`
- 配置文件: `config.py`

---

**版本**: v2.0.0  
**更新日期**: 2025-10-16  
**架构**: 消息队列模式
