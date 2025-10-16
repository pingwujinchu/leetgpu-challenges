# GPU资源阈值功能说明

## 🎯 功能概述

当GPU节点的显存利用率超过**90%**或GPU利用率超过**95%**时，系统将自动阻止新任务分配到该节点，实现任务排队机制。

## 🔧 工作原理

### 1. 资源检查流程

```
任务提交
    ↓
进入任务队列
    ↓
任务管理器选择Worker
    ↓
检查Worker GPU状态
    ↓
┌─────────────────────────┐
│ 显存 < 90% && GPU < 95%?│
└─────────────────────────┘
    ↓ YES              ↓ NO
分配任务            跳过该Worker
    ↓                   ↓
开始执行          检查下一个Worker
                        ↓
                  所有Worker都不可用?
                        ↓ YES
                    任务保持排队
                        ↓
                等待资源释放后自动分配
```

### 2. 阈值配置

在 `config.py` 中配置：

```python
# GPU资源限制配置
GPU_MEMORY_THRESHOLD = 90      # 显存利用率阈值（%）
GPU_UTILIZATION_THRESHOLD = 95  # GPU利用率阈值（%）
```

### 3. 实时检查

- 任务管理器在选择Worker前会实时查询GPU状态
- 通过HTTP请求获取Worker的GPU利用率和显存使用情况
- 自动跳过资源不足的Worker
- 如果所有Worker都不可用，任务保持在队列中

## 📊 使用示例

### 场景1: 单个Worker资源不足

```
状态:
  Worker 1: 显存 92% (超过阈值)
  Worker 2: 显存 55% (正常)
  Worker 3: 显存 78% (正常)

结果:
  新任务 → 跳过Worker 1 → 分配到Worker 2
```

### 场景2: 所有Worker资源不足

```
状态:
  Worker 1: 显存 95%
  Worker 2: 显存 93%
  Worker 3: 显存 91%

结果:
  新任务 → 检查所有Worker → 全部超阈值 → 任务排队
  
等待:
  Worker 2完成任务 → 显存降到 65% → 自动分配排队任务
```

### 场景3: 指定GPU型号

```
用户指定: RTX 4090

状态:
  Worker 1 (RTX 4090): 显存 92%
  Worker 2 (A100):     显存 60%
  Worker 3 (H100):     显存 55%

结果:
  检查RTX 4090 → 超阈值 → 不检查其他型号 → 任务排队
  等待RTX 4090资源释放
```

## 🖥️ 日志输出

任务分配时会输出详细日志：

```
[任务管理器] 为任务 abc-123 选择Worker...
[任务管理器] 检查Worker gpu-worker-1 (RTX 4090)...
[任务管理器] Worker gpu-worker-1 显存利用率 92.3% 超过阈值 90%，任务排队
[任务管理器] Worker gpu-worker-1 (RTX 4090) 资源不足，继续查找...
[任务管理器] 检查Worker gpu-worker-2 (A100)...
[任务管理器] Worker gpu-worker-2 资源充足
[任务管理器] 任务 abc-123 分配到Worker gpu-worker-2
```

## 🔍 监控和查看

### 1. Web界面

访问 http://localhost:5000 查看实时GPU状态：

```
🖥️ GPU节点资源监控

┌─ GPU Worker 1 ────────────────────┐
│ 🎮 RTX 4090                       │
│ 显存使用: ██████████░ 92.3% 🔴   │
│ GPU利用率: ████████░░ 78.5% 🟢   │
│ 状态: ⏸️ 不接受新任务（排队中）    │
└───────────────────────────────────┘
```

### 2. API查询

```python
import requests

# 查询GPU资源
response = requests.get('http://localhost:5000/api/gpu/resources')
data = response.json()

for gpu in data['resources']:
    memory_util = gpu['memory_utilization']
    gpu_util = gpu['gpu_utilization']
    
    if memory_util >= 90:
        print(f"{gpu['worker_name']}: 显存超阈值，不接受新任务")
    else:
        print(f"{gpu['worker_name']}: 资源充足，可接受任务")
```

### 3. 测试脚本

运行测试脚本查看当前状态：

```bash
python3 test_gpu_threshold.py
```

输出示例：

```
当前GPU资源状态:
────────────────────────────────────────

GPU Worker 1 (RTX 4090)
  显存使用: 92.3% 🔴 超过阈值
  GPU利用率: 78.5% 🟢 正常
  状态: ⏸️ 不接受新任务（排队中）

GPU Worker 2 (A100)
  显存使用: 55.2% 🟢 正常
  GPU利用率: 45.8% 🟢 正常
  状态: ✅ 可接受新任务
```

## ⚙️ 配置调整

### 修改阈值

编辑 `config.py`:

```python
# 调整为更严格的限制
GPU_MEMORY_THRESHOLD = 80      # 显存阈值改为80%
GPU_UTILIZATION_THRESHOLD = 90  # GPU利用率阈值改为90%

# 或更宽松的限制
GPU_MEMORY_THRESHOLD = 95      # 显存阈值改为95%
GPU_UTILIZATION_THRESHOLD = 98  # GPU利用率阈值改为98%
```

### 重启生效

修改配置后需要重启主节点：

```bash
# 停止当前服务（Ctrl+C）
# 重新启动
./start_all.sh
```

## 🎯 使用建议

### 1. 推荐阈值设置

| 场景 | 显存阈值 | GPU利用率阈值 | 说明 |
|------|---------|--------------|------|
| 保守（推荐） | 85% | 90% | 确保有足够余量 |
| 平衡（默认） | 90% | 95% | 兼顾利用率和稳定性 |
| 激进 | 95% | 98% | 最大化GPU利用率 |

### 2. 调整建议

- **高并发场景**: 降低阈值（80-85%），避免资源竞争
- **大任务场景**: 降低阈值（75-80%），预留更多显存
- **小任务场景**: 提高阈值（95%+），充分利用资源
- **生产环境**: 保守设置（85%），确保稳定性

### 3. 监控建议

- 定期查看GPU资源使用趋势
- 关注任务排队情况
- 根据实际使用调整阈值
- 考虑添加更多Worker节点

## 🚀 实际应用

### 示例：批量任务提交

```python
import requests
import time

# 提交10个任务
task_ids = []
for i in range(10):
    response = requests.post('http://localhost:5000/api/submit-task', json={
        'code': '...',
        'inputs': [...],
        'grid_size': [32],
        'block_size': [32]
    })
    task_ids.append(response.json()['task_id'])
    print(f"任务 {i+1} 已提交")

# 系统会自动:
# 1. 检查每个Worker的GPU状态
# 2. 选择资源充足的Worker
# 3. 如果所有Worker都满，任务排队
# 4. 资源释放后自动分配

# 等待所有任务完成
while True:
    completed = 0
    for task_id in task_ids:
        status = requests.get(f'http://localhost:5000/api/task/{task_id}')
        if status.json()['status'] == 'completed':
            completed += 1
    
    print(f"完成进度: {completed}/{len(task_ids)}")
    if completed == len(task_ids):
        break
    
    time.sleep(2)
```

## 📈 性能影响

- **额外延迟**: 每次选择Worker增加~50ms（GPU状态查询）
- **网络开销**: 轻量级HTTP请求
- **CPU开销**: 可忽略不计
- **整体影响**: 极小，可接受

## 🐛 故障排查

### 问题1: 任务一直排队

**可能原因**:
- 所有Worker显存都超过阈值
- Worker节点离线
- 阈值设置过低

**解决方法**:
```bash
# 1. 查看GPU状态
python3 test_gpu_threshold.py

# 2. 检查Worker是否在线
curl http://localhost:5001/health
curl http://localhost:5002/health
curl http://localhost:5003/health

# 3. 调整阈值（如果合适）
# 编辑 config.py，提高阈值
```

### 问题2: 任务分配不均

**可能原因**:
- 某些Worker资源更充足
- 任务指定了特定GPU型号

**解决方法**:
- 这是正常现象，系统优先选择资源充足的Worker
- 如需平衡负载，可考虑添加负载均衡策略

### 问题3: 阈值不生效

**可能原因**:
- 配置未重启生效
- 导入配置失败

**解决方法**:
```bash
# 1. 重启服务
# Ctrl+C 停止
./start_all.sh

# 2. 检查配置
python3 -c "from config import GPU_MEMORY_THRESHOLD; print(GPU_MEMORY_THRESHOLD)"
```

## 💡 高级用法

### 动态调整阈值（未来功能）

```python
# 未来可以通过API动态调整
requests.post('http://localhost:5000/api/config/threshold', json={
    'memory_threshold': 85,
    'gpu_threshold': 90
})
```

### 按任务优先级（未来功能）

```python
# 高优先级任务可以使用更高阈值
requests.post('http://localhost:5000/api/submit-task', json={
    'code': '...',
    'priority': 'high',  # 允许使用到95%
    # 普通任务使用90%阈值
})
```

## 📝 总结

GPU资源阈值功能确保系统稳定运行：

✅ **自动检测**: 实时查询GPU状态  
✅ **智能排队**: 资源不足时自动排队  
✅ **灵活配置**: 可调整阈值适应不同场景  
✅ **透明可见**: Web界面和日志实时反馈  
✅ **零干预**: 资源释放后自动分配  

---

**版本**: 1.1.0  
**更新日期**: 2025-10-16  
**相关文件**: `config.py`, `task_manager.py`
