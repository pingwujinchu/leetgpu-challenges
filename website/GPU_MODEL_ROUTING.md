# GPU型号路由功能

## 🎯 功能说明

每个GPU节点上的GPU型号不同，Worker只拉取支持其GPU型号的任务。

## 🏗️ 架构设计

### 问题场景

```
主节点提交任务，指定 gpu_model="RTX 4090"

GPU机器1: 4张 RTX 4090  ✅ 应该拉取
GPU机器2: 8张 A100      ❌ 不应该拉取
GPU机器3: 8张 H100      ❌ 不应该拉取
```

### 解决方案：多队列路由

```
主节点
  ↓ 提交任务
  ↓
判断 gpu_model
  ↓
gpu_model="RTX 4090"
  ↓
PUSH → [leetgpu:tasks:queue:RTX 4090]
  ↓
Worker (RTX 4090) PULL ← 只拉取RTX 4090队列
Worker (A100) PULL     ← 只拉取A100队列
Worker (H100) PULL     ← 只拉取H100队列
```

## 📊 队列结构

### Redis队列设计

```
通用队列（任意GPU可拉取）:
  leetgpu:tasks:queue

GPU型号特定队列:
  leetgpu:tasks:queue:RTX 4090
  leetgpu:tasks:queue:A100
  leetgpu:tasks:queue:H100
  leetgpu:tasks:queue:RTX 4080
  ...
```

### Worker拉取策略

**Worker配置了GPU型号**:
```python
# RTX 4090 Worker
gpu_models = ['RTX 4090']
task = mq.pull_task(gpu_models=['RTX 4090'])
# 拉取顺序: 
#   1. leetgpu:tasks:queue:RTX 4090 (优先)
#   2. leetgpu:tasks:queue (通用队列)
```

**Worker未配置GPU型号**:
```python
# 通用Worker
task = mq.pull_task(gpu_models=None)
# 只拉取: leetgpu:tasks:queue (通用队列)
```

## 🔄 工作流程

### 任务提交和路由

```
1. 用户提交任务
   task = {
       'code': '...',
       'gpu_model': 'RTX 4090'  # 指定GPU型号
   }
   
2. TaskManager处理
   if task.gpu_model:
       queue = 'leetgpu:tasks:queue:RTX 4090'
   else:
       queue = 'leetgpu:tasks:queue'
   
3. 推送到对应队列
   RPUSH queue task_json
   
4. Worker拉取
   RTX 4090 Worker:
     BLPOP ['leetgpu:tasks:queue:RTX 4090', 
            'leetgpu:tasks:queue']
     → 优先拉取RTX 4090队列
     → 其次拉取通用队列
   
   A100 Worker:
     BLPOP ['leetgpu:tasks:queue:A100',
            'leetgpu:tasks:queue']
     → 优先拉取A100队列
     → 其次拉取通用队列
```

## 🚀 使用方式

### 1. 启动Worker（指定GPU型号）

```bash
# GPU机器1 - RTX 4090
./start_worker_mq.sh \
    --id gpu-worker-1 \
    --gpu 0 \
    --gpu-model "RTX 4090" \
    --redis-host 192.168.1.100

# GPU机器2 - A100
./start_worker_mq.sh \
    --id gpu-worker-2 \
    --gpu 0 \
    --gpu-model "A100" \
    --redis-host 192.168.1.100

# GPU机器3 - H100
./start_worker_mq.sh \
    --id gpu-worker-3 \
    --gpu 0 \
    --gpu-model "H100" \
    --redis-host 192.168.1.100
```

### 2. 自动启动（检测GPU型号）

```bash
# 使用自动检测脚本
./start_multi_gpu_workers.sh

# 脚本会自动:
# 1. 检测GPU数量
# 2. 查询每张GPU的型号
# 3. 为每张GPU启动一个Worker
# 4. 每个Worker绑定到对应GPU型号的队列
```

### 3. 提交任务（指定GPU型号）

```python
from task_manager_mq import TaskManagerMQ

manager = TaskManagerMQ(...)

# 提交到RTX 4090队列
task_id = manager.submit_task(
    code='...',
    inputs=[...],
    grid_size=(32,),
    block_size=(32,),
    gpu_model='RTX 4090'  # 只有RTX 4090 Worker会拉取
)

# 提交到通用队列（任意GPU可拉取）
task_id = manager.submit_task(
    code='...',
    inputs=[...],
    grid_size=(32,),
    block_size=(32,),
    gpu_model=None  # 任意Worker都可以拉取
)
```

## 📊 示例场景

### 场景1: 不同GPU型号的机器

```
部署情况:
  GPU机器1: 4张 RTX 4090 (192.168.1.101)
  GPU机器2: 8张 A100     (192.168.1.102)
  GPU机器3: 8张 H100     (192.168.1.103)

启动Worker:
  机器1: 4个Worker，gpu_model="NVIDIA GeForce RTX 4090"
  机器2: 8个Worker，gpu_model="NVIDIA A100-SXM4-80GB"
  机器3: 8个Worker，gpu_model="NVIDIA H100 80GB HBM3"

用户提交:
  任务A: gpu_model="RTX 4090"
    → 推送到: leetgpu:tasks:queue:NVIDIA GeForce RTX 4090
    → 只有机器1的4个Worker会拉取

  任务B: gpu_model="A100"
    → 推送到: leetgpu:tasks:queue:NVIDIA A100-SXM4-80GB
    → 只有机器2的8个Worker会拉取

  任务C: gpu_model=None
    → 推送到: leetgpu:tasks:queue (通用队列)
    → 所有Worker都可以拉取
```

### 场景2: 混合GPU型号的机器

```
部署情况:
  GPU机器: 2张 RTX 4090 + 2张 RTX 3090

启动Worker:
  Worker 1: GPU 0, gpu_model="RTX 4090"
  Worker 2: GPU 1, gpu_model="RTX 4090"
  Worker 3: GPU 2, gpu_model="RTX 3090"
  Worker 4: GPU 3, gpu_model="RTX 3090"

用户提交:
  任务指定 RTX 4090 → Worker 1和2竞争
  任务指定 RTX 3090 → Worker 3和4竞争
  任务未指定型号   → 所有Worker竞争
```

## 🔍 GPU型号匹配规则

### 精确匹配

Worker的`gpu_model`必须与任务的`gpu_model`完全匹配：

```python
任务: gpu_model = "RTX 4090"
Worker: gpu_model = "NVIDIA GeForce RTX 4090"
匹配结果: ❌ 不匹配（完整名称不同）
```

### 建议：规范化GPU型号

**方式1: 使用简化名称**
```python
# 配置中统一使用简化名称
GPU型号实际名称: "NVIDIA GeForce RTX 4090"
配置中使用:      "RTX 4090"

# 或创建映射
GPU_NAME_MAPPING = {
    "NVIDIA GeForce RTX 4090": "RTX 4090",
    "NVIDIA A100-SXM4-80GB": "A100",
    "NVIDIA H100 80GB HBM3": "H100",
}
```

**方式2: Worker启动时指定**
```bash
# 手动指定简化名称
./start_worker_mq.sh \
    --id worker-1 \
    --gpu 0 \
    --gpu-model "RTX 4090"  # 使用简化名称
```

## 🛠️ 实现细节

### 1. 消息队列模块

**修改 `message_queue.py`**:

```python
# 推送任务
def push_task(self, task_data, gpu_model=None):
    if gpu_model:
        queue = f"leetgpu:tasks:queue:{gpu_model}"
    else:
        queue = "leetgpu:tasks:queue"
    
    redis.rpush(queue, task_json)

# 拉取任务
def pull_task(self, gpu_models=None, timeout=1):
    queues = []
    
    if gpu_models:
        # 添加特定GPU型号队列
        for model in gpu_models:
            queues.append(f"leetgpu:tasks:queue:{model}")
    
    # 添加通用队列
    queues.append("leetgpu:tasks:queue")
    
    # BLPOP支持多个队列，按顺序优先级
    result = redis.blpop(queues, timeout)
    return result
```

### 2. GPU Worker

**修改 `gpu_worker_mq.py`**:

```python
class GPUWorkerMQ:
    def __init__(self, worker_id, gpu_id, gpu_model=None, ...):
        self.gpu_model = gpu_model
    
    def _worker_loop(self):
        while self.running:
            # 只拉取匹配GPU型号的任务
            gpu_models = [self.gpu_model] if self.gpu_model else None
            task = self.message_queue.pull_task(
                gpu_models=gpu_models,
                timeout=1
            )
```

### 3. 任务管理器

**修改 `task_manager_mq.py`**:

```python
def submit_task(self, code, ..., gpu_model=None):
    task_data = {...}
    
    # 推送到对应GPU型号的队列
    self.message_queue.push_task(task_data, gpu_model=gpu_model)
```

## 📈 监控和调试

### 查看所有队列

```bash
# 查看所有任务队列
redis-cli KEYS 'leetgpu:tasks:queue*'

# 输出示例:
# leetgpu:tasks:queue
# leetgpu:tasks:queue:RTX 4090
# leetgpu:tasks:queue:A100
# leetgpu:tasks:queue:H100
```

### 查看队列大小

```bash
# 通用队列
redis-cli LLEN leetgpu:tasks:queue

# RTX 4090队列
redis-cli LLEN "leetgpu:tasks:queue:RTX 4090"

# A100队列
redis-cli LLEN "leetgpu:tasks:queue:A100"
```

### 查看Worker监听的队列

```bash
# 查看Worker日志
tail -f logs/worker-gpu-server-1-gpu-0.log

# 应该看到类似输出:
# Worker GPU型号: RTX 4090
# 监听队列: ['leetgpu:tasks:queue:RTX 4090', 'leetgpu:tasks:queue']
```

## 🧪 测试示例

```python
from message_queue import get_message_queue

mq = get_message_queue()

# 推送RTX 4090任务
task1 = {'task_id': 'task-1', 'code': '...', 'gpu_model': 'RTX 4090'}
mq.push_task(task1, gpu_model='RTX 4090')
# → 推送到: leetgpu:tasks:queue:RTX 4090

# 推送A100任务
task2 = {'task_id': 'task-2', 'code': '...', 'gpu_model': 'A100'}
mq.push_task(task2, gpu_model='A100')
# → 推送到: leetgpu:tasks:queue:A100

# 推送通用任务
task3 = {'task_id': 'task-3', 'code': '...', 'gpu_model': None}
mq.push_task(task3, gpu_model=None)
# → 推送到: leetgpu:tasks:queue

# RTX 4090 Worker拉取
task = mq.pull_task(gpu_models=['RTX 4090'])
# → 从 leetgpu:tasks:queue:RTX 4090 拉取task-1

# A100 Worker拉取
task = mq.pull_task(gpu_models=['A100'])
# → 从 leetgpu:tasks:queue:A100 拉取task-2

# 通用Worker拉取
task = mq.pull_task(gpu_models=None)
# → 从 leetgpu:tasks:queue 拉取task-3
```

## 🎯 优势

### 1. 资源隔离
- 不同GPU型号的任务互不干扰
- RTX 4090任务只在RTX 4090上执行
- 避免GPU能力不匹配

### 2. 负载均衡
- 同型号GPU自动竞争任务
- 机器1的4张RTX 4090竞争RTX 4090任务
- 快的GPU处理更多任务

### 3. 灵活性
- 支持混合GPU部署
- 支持通用任务（任意GPU）
- 动态添加新型号

### 4. 兼容性
- 完全向后兼容
- 不指定gpu_model使用通用队列
- 旧代码无需修改

## 📝 配置示例

### config_multi_gpu.py

```python
GPU_WORKERS = [
    # GPU机器1 - 4张RTX 4090
    {
        'id': 'gpu-server-1-gpu-0',
        'gpu_device_id': 0,
        'gpu_model': 'RTX 4090',  # 简化名称
        ...
    },
    {
        'id': 'gpu-server-1-gpu-1',
        'gpu_device_id': 1,
        'gpu_model': 'RTX 4090',
        ...
    },
    # ...更多RTX 4090
    
    # GPU机器2 - 8张A100
    {
        'id': 'gpu-server-2-gpu-0',
        'gpu_device_id': 0,
        'gpu_model': 'A100',
        ...
    },
    # ...更多A100
]
```

### 启动Worker

```bash
# GPU机器1 - 自动检测并启动所有RTX 4090
cd /workspace/website
export REDIS_HOST=192.168.1.100
./start_multi_gpu_workers.sh

# 或手动指定
./start_worker_mq.sh \
    --id gpu-1-0 \
    --gpu 0 \
    --gpu-model "RTX 4090" \
    --redis-host 192.168.1.100
```

## 🔍 监控和验证

### 查看队列分布

```python
from message_queue import get_message_queue

mq = get_message_queue(host='192.168.1.100')

# 获取所有队列大小
sizes = mq.get_all_queue_sizes()
for queue_name, size in sizes.items():
    print(f"{queue_name}: {size} 任务")

# 输出示例:
# 通用队列: 5 任务
# RTX 4090: 10 任务
# A100: 3 任务
# H100: 7 任务
```

### 查看Worker分布

```bash
# 查看所有Worker
redis-cli -h 192.168.1.100 KEYS 'leetgpu:workers:status:*'

# 查看特定GPU型号的Worker
redis-cli -h 192.168.1.100 KEYS 'leetgpu:workers:status:*4090*'
redis-cli -h 192.168.1.100 KEYS 'leetgpu:workers:status:*A100*'
```

## 🐛 故障排查

### 问题1: Worker拉不到任务

**可能原因**:
- GPU型号名称不匹配
- 队列名称错误

**解决方法**:
```bash
# 1. 检查Worker的GPU型号
grep "GPU型号" logs/worker-*.log

# 2. 检查队列名称
redis-cli KEYS 'leetgpu:tasks:queue:*'

# 3. 查看任务推送到哪个队列
# 主节点日志会显示: "任务推送到 RTX 4090 队列"

# 4. GPU型号名称标准化
# 确保提交任务时的gpu_model与Worker的gpu_model一致
```

### 问题2: GPU型号名称不一致

```bash
# nvidia-smi显示完整名称
nvidia-smi --query-gpu=name --format=csv,noheader

# 输出可能是:
# NVIDIA GeForce RTX 4090

# 建议统一使用简化名称:
# --gpu-model "RTX 4090"
```

### 问题3: 任务只在部分GPU上执行

- 检查是否指定了gpu_model
- 验证Worker是否都在运行
- 查看队列分布是否均衡

## 💡 最佳实践

### 1. GPU型号命名规范

建议使用简化统一的命名：

| nvidia-smi显示 | 建议配置名称 |
|---------------|-------------|
| NVIDIA GeForce RTX 4090 | RTX 4090 |
| NVIDIA A100-SXM4-80GB | A100 |
| NVIDIA H100 80GB HBM3 | H100 |
| NVIDIA GeForce RTX 3090 | RTX 3090 |

### 2. 启动Worker

**自动检测模式**（推荐）:
```bash
# 自动检测GPU型号并启动
./start_multi_gpu_workers.sh
```

**手动指定模式**:
```bash
# 适合混合GPU或需要精确控制
./start_worker_mq.sh --gpu 0 --gpu-model "RTX 4090"
./start_worker_mq.sh --gpu 1 --gpu-model "RTX 4090"
./start_worker_mq.sh --gpu 2 --gpu-model "RTX 3090"
./start_worker_mq.sh --gpu 3 --gpu-model "RTX 3090"
```

### 3. 提交任务

```python
# 需要特定GPU
manager.submit_task(..., gpu_model='RTX 4090')

# 任意GPU都可以
manager.submit_task(..., gpu_model=None)
```

### 4. 监控队列

定期检查各队列的积压情况：
```bash
# 创建监控脚本
watch -n 5 'redis-cli KEYS "leetgpu:tasks:queue:*" | xargs -I {} sh -c "echo -n \"{}: \"; redis-cli LLEN {}"'
```

## 🎯 使用建议

1. **统一命名**: 在config.py和启动脚本中使用一致的GPU型号名称
2. **自动检测**: 使用start_multi_gpu_workers.sh自动检测GPU型号
3. **队列监控**: 定期检查各队列大小，避免某些队列积压
4. **通用任务**: 对不依赖特定GPU的任务使用gpu_model=None
5. **文档化**: 记录每台机器的GPU型号配置

## 📊 性能影响

- **额外开销**: 几乎为0（Redis BLPOP支持多队列）
- **隔离性**: 完美（不同队列完全隔离）
- **灵活性**: 高（支持动态添加新GPU型号）

---

**功能**: GPU型号路由  
**版本**: v2.2.0  
**状态**: ✅ 完成

🎯 **Worker只拉取匹配GPU型号的任务！**
