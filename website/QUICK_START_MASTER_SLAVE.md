# LeetGPU 主从架构 - 快速开始

## 快速开始（5分钟）

### 1. 安装依赖

```bash
cd website
pip install -r requirements.txt
```

### 2. 启动所有节点

```bash
./start_all.sh
```

这会自动启动：
- 3个GPU Worker节点（后台）
- 1个主节点（前台，监听在5000端口）

### 3. 访问网站

打开浏览器访问: http://localhost:5000

你将看到：
- 题库列表
- GPU节点资源监控面板（实时更新）
- 每个GPU节点的利用率、显存使用、温度等信息

### 4. 提交任务（通过Python脚本）

在另一个终端运行：

```bash
python3 example_task_submission.py
```

选择选项3提交一个向量加法任务，系统会：
1. 自动选择合适的GPU Worker
2. 编译并执行CUDA代码
3. 返回计算结果

## 架构说明

```
主节点 (Port 5000)
    ├── Web服务
    ├── 任务分发器
    └── GPU监控器
        │
        ├─> Worker 1: RTX 4090 (Port 5001)
        ├─> Worker 2: A100     (Port 5002)
        └─> Worker 3: H100     (Port 5003)
```

## 核心功能

### 1. 实时GPU监控

主页面会显示所有GPU节点的实时状态：
- GPU利用率
- 显存使用率
- 温度
- 功耗
- 在线/离线状态
- 可用/忙碌状态

数据每5秒自动刷新。

### 2. 智能任务分发

提交任务时可以：
- 指定GPU型号（如RTX 4090、A100等）
- 自动选择空闲的GPU
- 队列管理和优先级调度

### 3. CUDA JIT执行

用户代码会被自动：
- 验证语法
- 编译为CUDA核函数
- 在指定GPU上执行
- 返回结果

## API使用示例

### 提交任务

```python
import requests
import numpy as np

# 准备CUDA代码
code = """
def vector_add(a, b, c):
    idx = cuda.grid(1)
    if idx < c.size:
        c[idx] = a[idx] + b[idx]
"""

# 准备数据
n = 1000
a = np.arange(n, dtype=np.float32)
b = np.arange(n, dtype=np.float32)
c = np.zeros(n, dtype=np.float32)

# 提交任务
response = requests.post('http://localhost:5000/api/submit-task', json={
    'code': code,
    'inputs': [
        {'data': a.tolist(), 'shape': a.shape, 'dtype': 'float32'},
        {'data': b.tolist(), 'shape': b.shape, 'dtype': 'float32'},
        {'data': c.tolist(), 'shape': c.shape, 'dtype': 'float32'}
    ],
    'grid_size': [32],
    'block_size': [32],
    'gpu_model': 'RTX 4090'  # 可选
})

task_id = response.json()['task_id']
print(f"任务ID: {task_id}")
```

### 查询任务状态

```python
response = requests.get(f'http://localhost:5000/api/task/{task_id}')
status = response.json()

if status['status'] == 'completed':
    print("任务完成！")
    print(f"结果: {status['result']}")
```

### 获取GPU资源状态

```python
response = requests.get('http://localhost:5000/api/gpu/resources')
data = response.json()

for gpu in data['resources']:
    print(f"{gpu['worker_name']}: {gpu['gpu_utilization']}% @ {gpu['temperature']}°C")
```

## 分别启动节点（高级）

### 启动主节点

```bash
./start_master.sh
```

### 启动Worker节点

```bash
# Worker 1 - RTX 4090
./start_worker.sh --id gpu-worker-1 --port 5001 --gpu 0

# Worker 2 - A100
./start_worker.sh --id gpu-worker-2 --port 5002 --gpu 0

# Worker 3 - H100
./start_worker.sh --id gpu-worker-3 --port 5003 --gpu 0
```

## 配置自定义GPU节点

编辑 `config.py`:

```python
GPU_WORKERS = [
    {
        'id': 'my-gpu-1',
        'name': 'My GPU 1',
        'host': 'gpu-server-1.local',  # 远程主机
        'port': 5001,
        'gpu_model': 'RTX 4090',
        'gpu_memory': '24GB',
        'compute_capability': '8.9'
    },
    # 添加更多Worker...
]
```

## 常见问题

### Q: Worker节点显示离线？

A: 检查：
1. Worker进程是否运行: `ps aux | grep gpu_worker`
2. 端口是否被占用: `netstat -anp | grep 5001`
3. 防火墙设置

### Q: 任务一直处于queued状态？

A: 可能原因：
1. 所有Worker都在忙碌中
2. 指定的GPU型号没有可用Worker
3. Worker节点离线

### Q: GPU利用率显示为0？

A: 这是正常的，在模拟模式下会生成随机数据。如果有真实GPU，需要关闭模拟模式：

```python
# 在 app.py 中修改
gpu_monitor = GPUMonitor(simulation_mode=False)
```

### Q: 如何添加更多GPU型号？

A: 在 `config.py` 中的 `GPU_WORKERS` 列表中添加新配置即可。

## 下一步

1. 查看完整架构文档: `MASTER_SLAVE_ARCHITECTURE.md`
2. 运行示例脚本: `python3 example_task_submission.py`
3. 在Web界面查看GPU监控: http://localhost:5000
4. 浏览题库并提交答案

## 停止服务

在启动主节点的终端按 `Ctrl+C`，系统会自动关闭所有Worker节点。

或者手动停止：

```bash
pkill -f gpu_worker.py
pkill -f app.py
```

## 技术栈

- **后端**: Flask (Python)
- **GPU计算**: Numba CUDA JIT
- **GPU监控**: pynvml
- **前端**: Vanilla JavaScript + CSS
- **通信**: RESTful API

## 许可证

本项目采用MIT许可证。
