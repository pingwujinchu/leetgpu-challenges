# LeetGPU 主从架构说明

## 架构概述

LeetGPU采用主从（Master-Slave）架构设计，将网站服务和GPU计算任务分离：

- **主节点（Master Node）**: 部署在CPU节点上，负责Web服务、任务分发和资源监控
- **从节点（GPU Worker Nodes）**: 部署在GPU节点上，负责执行实际的CUDA计算任务

```
┌─────────────────────────────────────────────────────────────┐
│                      主节点 (Master Node)                     │
│                     CPU节点 - Port 5000                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Web服务    │  │  任务管理器   │  │  GPU监控器    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
┌───────────▼────────┐ ┌─────▼──────────┐ ┌───▼──────────────┐
│  GPU Worker 1      │ │  GPU Worker 2  │ │  GPU Worker 3    │
│  RTX 4090 24GB     │ │  A100 40GB     │ │  H100 80GB       │
│  Port 5001         │ │  Port 5002     │ │  Port 5003       │
│  ┌──────────────┐  │ │ ┌────────────┐ │ │ ┌──────────────┐ │
│  │ CUDA执行引擎 │  │ │ │CUDA执行引擎│ │ │ │CUDA执行引擎  │ │
│  └──────────────┘  │ │ └────────────┘ │ │ └──────────────┘ │
└────────────────────┘ └────────────────┘ └──────────────────┘
```

## 核心组件

### 1. 配置文件 (`config.py`)

定义主节点和所有GPU Worker节点的配置信息：
- GPU型号和规格
- 网络地址和端口
- 任务超时配置
- 监控间隔设置

### 2. CUDA JIT封装器 (`cuda_jit_wrapper.py`)

将用户提交的Python代码封装为CUDA JIT可执行的核函数：
- 代码验证和语法检查
- 自动编译为CUDA核函数
- 内核执行和结果返回
- 错误处理和异常捕获

### 3. GPU监控器 (`gpu_monitor.py`)

实时监控GPU资源使用情况：
- GPU利用率
- 显存使用率
- 温度
- 功耗
- 支持模拟模式（无GPU环境下测试）

### 4. 任务管理器 (`task_manager.py`)

负责任务的提交、分发和状态管理：
- 任务队列管理
- 智能Worker选择（支持指定GPU型号）
- 任务状态跟踪
- 自动重试和错误处理
- Worker健康检查

### 5. GPU Worker服务 (`gpu_worker.py`)

从节点服务，接收并执行GPU任务：
- 接收任务请求
- 执行CUDA JIT编译和运行
- 返回计算结果
- 提供GPU状态查询接口

### 6. 主节点服务 (`app.py`)

主Web服务器，提供以下功能：
- 题库管理和展示
- 任务提交接口
- GPU资源监控展示
- 集群状态查询

## API接口

### 任务提交

```http
POST /api/submit-task
Content-Type: application/json

{
  "code": "def vector_add(a, b, c): ...",
  "inputs": [...],
  "grid_size": [32],
  "block_size": [32],
  "gpu_model": "RTX 4090"  // 可选，指定GPU型号
}
```

### 查询任务状态

```http
GET /api/task/{task_id}

Response:
{
  "task_id": "uuid",
  "status": "completed",
  "result": [...],
  "worker_id": "gpu-worker-1"
}
```

### 获取GPU资源状态

```http
GET /api/gpu/resources

Response:
{
  "total_workers": 3,
  "resources": [
    {
      "worker_id": "gpu-worker-1",
      "worker_name": "GPU Worker 1",
      "gpu_model": "RTX 4090",
      "gpu_utilization": 45.2,
      "memory_utilization": 60.1,
      "temperature": 65,
      "power_usage": 280.5,
      "status": "available",
      "online": true
    },
    ...
  ]
}
```

### 获取集群统计

```http
GET /api/cluster/stats

Response:
{
  "total_workers": 3,
  "online_workers": 3,
  "busy_workers": 1,
  "available_workers": 2,
  "total_tasks": 10,
  "task_stats": {
    "completed": 7,
    "running": 1,
    "queued": 2
  }
}
```

## 启动方式

### 方式1: 启动所有节点（推荐）

```bash
cd website
chmod +x start_all.sh
./start_all.sh
```

这会自动启动：
- 3个GPU Worker节点（后台）
- 1个主节点（前台）

### 方式2: 分别启动

#### 启动主节点

```bash
cd website
chmod +x start_master.sh
./start_master.sh
```

#### 启动Worker节点

```bash
# Worker 1
./start_worker.sh --id gpu-worker-1 --port 5001 --gpu 0

# Worker 2
./start_worker.sh --id gpu-worker-2 --port 5002 --gpu 0

# Worker 3
./start_worker.sh --id gpu-worker-3 --port 5003 --gpu 0
```

### 方式3: 手动启动（开发调试）

```bash
# 启动主节点
python3 app.py

# 启动Worker节点（在不同终端）
python3 gpu_worker.py --id gpu-worker-1 --port 5001 --gpu 0
python3 gpu_worker.py --id gpu-worker-2 --port 5002 --gpu 0
python3 gpu_worker.py --id gpu-worker-3 --port 5003 --gpu 0
```

## 任务执行流程

1. **用户提交任务**: 用户在Web界面提交CUDA代码和输入数据
2. **任务入队**: 主节点将任务加入队列
3. **Worker选择**: 任务管理器根据GPU型号要求选择合适的Worker
4. **任务分发**: 主节点将任务发送到选中的Worker
5. **代码编译**: Worker使用CUDA JIT编译用户代码
6. **执行计算**: Worker在GPU上执行计算任务
7. **结果返回**: Worker将结果返回给主节点
8. **状态更新**: 主节点更新任务状态，用户可查询结果

## GPU资源监控

主节点实时监控所有Worker节点的GPU使用情况，包括：

- **实时指标**:
  - GPU利用率（百分比）
  - 显存使用率（百分比）
  - 温度（摄氏度）
  - 功耗（瓦特）

- **节点状态**:
  - 在线/离线
  - 可用/忙碌
  - 运行任务数

- **更新频率**: 每5秒自动刷新

## 扩展性

### 添加新的GPU Worker节点

1. 编辑 `config.py`，在 `GPU_WORKERS` 列表中添加新节点配置：

```python
{
    'id': 'gpu-worker-4',
    'name': 'GPU Worker 4',
    'host': 'localhost',
    'port': 5004,
    'gpu_model': 'RTX 4080',
    'gpu_memory': '16GB',
    'compute_capability': '8.9'
}
```

2. 启动新的Worker节点：

```bash
./start_worker.sh --id gpu-worker-4 --port 5004 --gpu 0
```

3. 重启主节点以加载新配置

### 支持新的GPU型号

只需在配置文件中添加相应的GPU型号信息即可，系统会自动识别和使用。

## 故障处理

### Worker节点离线

- 系统会自动标记Worker为离线状态
- 队列中的任务会等待其他可用Worker
- 可以随时重启Worker节点

### 任务超时

- 任务会被标记为超时状态
- Worker会自动释放
- 可以重新提交任务

### 主节点重启

- Worker节点会继续运行
- 主节点重启后会重新建立连接
- 队列中的任务会丢失，需要重新提交

## 安全建议

1. **生产环境部署**:
   - 使用反向代理（Nginx/Apache）
   - 启用HTTPS
   - 配置防火墙规则
   - 限制Worker节点访问

2. **代码执行安全**:
   - 对用户提交的代码进行沙箱隔离
   - 设置资源限制（内存、计算时间）
   - 禁止危险的系统调用

3. **网络安全**:
   - Worker节点仅接受主节点的连接
   - 使用API密钥认证
   - 加密敏感数据传输

## 性能优化

1. **任务调度**:
   - 根据GPU负载动态分配任务
   - 优先使用空闲的Worker
   - 批处理小任务以减少通信开销

2. **监控优化**:
   - 根据需要调整监控频率
   - 使用缓存减少重复查询
   - 异步更新GPU状态

3. **网络优化**:
   - 使用连接池复用HTTP连接
   - 压缩大数据传输
   - 本地缓存常用数据

## 未来扩展

- [ ] 支持分布式Redis任务队列
- [ ] 添加任务优先级机制
- [ ] 实现负载均衡算法
- [ ] 支持GPU集群管理
- [ ] 添加任务执行历史记录
- [ ] 实现用户认证和权限管理
- [ ] 支持多租户隔离
- [ ] 集成Prometheus监控
- [ ] 添加任务执行可视化
- [ ] 支持任务依赖关系

## 联系与支持

如有问题或建议，请查看项目文档或提交Issue。
