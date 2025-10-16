# 🚀 消息队列架构 - 快速开始

## 📋 需求实现

✅ **主从节点通过消息队列衔接**  
✅ **任务推送到消息队列**  
✅ **从节点从队列拉取任务执行**  

## ⚡ 5分钟快速开始

### 1. 安装依赖

```bash
cd /workspace/website
pip install redis==5.0.1
```

### 2. 启动Redis（3选1）

**选项A: 本地安装**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server && sudo systemctl start redis

# macOS
brew install redis && brew services start redis
```

**选项B: Docker**
```bash
docker run -d -p 6379:6379 --name redis redis:alpine
```

**选项C: 无Redis（内存模式）**
- 直接跳过，系统自动使用内存队列
- ⚠️ 无持久化，重启丢失数据

### 3. 启动Worker（一键）

```bash
./start_all_mq.sh
```

输出：
```
✅ Redis服务正在运行
启动 Worker 1 (RTX 4090)...
启动 Worker 2 (A100)...
启动 Worker 3 (H100)...
✅ Worker节点已启动（后台运行）
```

### 4. 提交任务

```python
from task_manager_mq import TaskManagerMQ
from config import GPU_WORKERS, REDIS_HOST, REDIS_PORT, REDIS_DB

# 初始化
manager = TaskManagerMQ(GPU_WORKERS, REDIS_HOST, REDIS_PORT, REDIS_DB)
manager.start_monitor()

# 提交任务
task_id = manager.submit_task(
    code='''
def vector_add(a, b, c):
    idx = cuda.grid(1)
    if idx < c.size:
        c[idx] = a[idx] + b[idx]
''',
    inputs=[],
    grid_size=(32,),
    block_size=(32,)
)

# 查询结果
import time
time.sleep(2)
status = manager.get_task_status(task_id)
print(f"状态: {status['status']}")
```

## 🎯 工作原理

```
用户 → 主节点 → PUSH任务 → [Redis队列]
                                    ↓
                            Worker竞争拉取
                                    ↓
                            检查GPU资源
                                    ↓
                            执行CUDA JIT
                                    ↓
                         PUSH结果到Redis
                                    ↓
主节点 ← 查询结果 ←───────────────────┘
```

## 📊 架构特点

| 特性 | 说明 |
|------|------|
| 解耦 | 主从节点完全独立 |
| 负载均衡 | Worker自动竞争任务 |
| 高可用 | Worker故障不影响系统 |
| 可扩展 | 随时添加Worker |
| 持久化 | Redis保证任务不丢失 |
| 资源保护 | GPU超90%自动排队 |

## 🔍 监控命令

```bash
# 查看队列大小
redis-cli LLEN leetgpu:tasks:queue

# 查看在线Worker
redis-cli KEYS 'leetgpu:workers:status:*'

# 查看Worker状态
redis-cli GET leetgpu:workers:status:gpu-worker-1

# Worker日志
tail -f logs/worker1_mq.log
```

## 🧪 测试

```bash
# 测试消息队列
python3 test_message_queue.py queue

# 测试任务管理器
python3 test_message_queue.py manager
```

## 📂 文件结构

```
website/
├── message_queue.py          # 消息队列模块 ✨新增
├── task_manager_mq.py        # 任务管理器MQ版 ✨新增
├── gpu_worker_mq.py          # Worker MQ版 ✨新增
├── start_worker_mq.sh        # Worker启动脚本 ✨新增
├── start_all_mq.sh           # 一键启动 ✨新增
├── test_message_queue.py     # 测试套件 ✨新增
└── requirements.txt          # 添加redis依赖 ✨修改
```

## 🔄 与旧版本对比

### HTTP模式（v1.x）
```python
# 主节点直接POST到Worker
response = requests.post(f"http://worker:5001/execute", json=task)
```

### 消息队列模式（v2.0）
```python
# 主节点PUSH到队列
mq.push_task(task)

# Worker自动PULL
task = mq.pull_task()
```

## ⚙️ 配置

`config.py` 中的Redis配置：

```python
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
```

## 🐛 常见问题

### Q: Redis连接失败？

```bash
# 检查Redis
redis-cli ping
# 应返回: PONG

# 启动Redis
redis-server
```

### Q: Worker不拉取任务？

```bash
# 查看Worker日志
tail -f logs/worker1_mq.log

# 检查GPU资源（可能超阈值）
# 日志会显示: "显存利用率 92% 超过阈值 90%"
```

### Q: 如何清空队列？

```bash
redis-cli DEL leetgpu:tasks:queue
```

## 📚 详细文档

- **完整架构**: `MESSAGE_QUEUE_ARCHITECTURE.md`
- **实现报告**: `/workspace/MESSAGE_QUEUE_IMPLEMENTATION.md`

## 🎁 优势

✅ **零维护**: Worker自动注册和心跳  
✅ **自动均衡**: 快的Worker处理更多  
✅ **动态扩展**: 启动Worker即可加入  
✅ **故障恢复**: Worker崩溃任务不丢失  
✅ **资源保护**: 超阈值自动排队  

## 🚦 快速命令

```bash
# 完整流程
pip install redis
redis-server &
./start_all_mq.sh
python3 test_message_queue.py manager

# 停止
# Ctrl+C 停止Worker
redis-cli SHUTDOWN
```

---

**版本**: v2.0.0  
**模式**: 消息队列  
**状态**: ✅ 可用

🎉 **消息队列架构已实现，enjoy！**
