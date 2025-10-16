# 更新日志

## [1.1.0] - 2025-10-16

### 新增功能
- ✨ **GPU资源阈值检测**: 当GPU显存利用率超过90%或GPU利用率超过95%时，自动阻止新任务分配到该节点
- ✨ **智能任务排队**: 所有Worker资源不足时，任务自动排队等待
- ✨ **实时资源检查**: 任务分配前实时查询Worker的GPU状态
- ✨ **可配置阈值**: 通过config.py配置显存和GPU利用率阈值
- 📚 **新增文档**: GPU_THRESHOLD_FEATURE.md - 详细的功能说明文档
- 🧪 **新增测试**: test_gpu_threshold.py - 阈值功能测试脚本

### 修改
- 🔧 修改 `task_manager.py`: 添加 `check_worker_resources()` 方法
- 🔧 修改 `task_manager.py`: 更新 `find_suitable_worker()` 方法，集成资源检查
- 🔧 修改 `config.py`: 添加 `GPU_MEMORY_THRESHOLD` 和 `GPU_UTILIZATION_THRESHOLD` 配置项
- 📝 更新 `README_MASTER_SLAVE.md`: 添加资源阈值功能说明

### 工作原理
```
任务分配流程:
1. 检查Worker是否在线
2. 检查Worker状态（available/busy）
3. 查询Worker的GPU资源使用情况
4. 验证显存利用率 < 90%
5. 验证GPU利用率 < 95%
6. 资源充足 → 分配任务
7. 资源不足 → 跳过该Worker，检查下一个
8. 所有Worker都不可用 → 任务保持排队
```

### 配置示例
```python
# config.py
GPU_MEMORY_THRESHOLD = 90      # 显存阈值（%）
GPU_UTILIZATION_THRESHOLD = 95  # GPU利用率阈值（%）
```

### 使用示例
```bash
# 测试阈值功能
python3 test_gpu_threshold.py

# 查看实时GPU状态
# 访问 http://localhost:5000
```

### 日志输出
```
[任务管理器] Worker gpu-worker-1 显存利用率 92.0% 超过阈值 90%，任务排队
[任务管理器] Worker gpu-worker-1 (RTX 4090) 资源不足，继续查找...
[任务管理器] Worker gpu-worker-2 资源充足
[任务管理器] 任务分配到Worker gpu-worker-2 (A100)
```

---

## [1.0.0] - 2025-10-16

### 初始发布
- 🎉 完整的主从架构实现
- 🚀 主节点（CPU）+ 从节点（GPU）分离部署
- 🔧 CUDA JIT自动封装和执行
- 📊 实时GPU资源监控
- 🎯 智能任务分发系统
- 🌐 Web界面展示
- 📡 RESTful API接口
- 📚 完整文档（4份）
- 🧪 测试套件

### 核心模块
- `config.py` - 配置管理
- `cuda_jit_wrapper.py` - CUDA JIT封装
- `gpu_monitor.py` - GPU监控
- `task_manager.py` - 任务管理
- `gpu_worker.py` - Worker节点服务
- `app.py` - 主节点服务

### 启动脚本
- `start_master.sh` - 启动主节点
- `start_worker.sh` - 启动Worker节点
- `start_all.sh` - 一键启动

### 示例和测试
- `example_task_submission.py` - 使用示例
- `test_master_slave.py` - 功能测试

### 文档
- `MASTER_SLAVE_ARCHITECTURE.md` - 架构文档
- `QUICK_START_MASTER_SLAVE.md` - 快速开始
- `IMPLEMENTATION_SUMMARY.md` - 实现总结
- `README_MASTER_SLAVE.md` - 总体说明

### 功能特性
- ✅ 支持多GPU节点
- ✅ GPU型号选择（RTX 4090/A100/H100）
- ✅ 实时资源监控（利用率/显存/温度/功耗）
- ✅ 任务队列管理
- ✅ Worker健康检查
- ✅ 模拟模式支持
- ✅ 响应式Web界面

---

## 未来计划

### v1.2.0 (计划中)
- [ ] Redis任务队列集成
- [ ] 任务优先级机制
- [ ] 动态阈值调整API
- [ ] Worker自动扩缩容
- [ ] Prometheus监控集成

### v1.3.0 (计划中)
- [ ] 用户认证系统
- [ ] 多租户支持
- [ ] GPU资源配额管理
- [ ] 任务执行历史记录
- [ ] 性能统计和分析

### v2.0.0 (远期)
- [ ] Kubernetes部署支持
- [ ] 分布式任务调度
- [ ] GPU集群管理
- [ ] 自动故障转移
- [ ] 负载均衡优化

---

## 升级指南

### 从 v1.0.0 升级到 v1.1.0

1. 更新代码文件:
   ```bash
   git pull origin master
   ```

2. 无需修改现有配置（使用默认阈值）

3. 重启服务:
   ```bash
   # Ctrl+C 停止当前服务
   ./start_all.sh
   ```

4. （可选）自定义阈值:
   ```python
   # 编辑 config.py
   GPU_MEMORY_THRESHOLD = 85  # 调整为85%
   ```

5. 测试新功能:
   ```bash
   python3 test_gpu_threshold.py
   ```

### 兼容性说明
- ✅ 完全向后兼容
- ✅ 现有API不受影响
- ✅ 配置文件兼容
- ✅ 数据格式兼容

---

**维护者**: AI Assistant  
**项目**: LeetGPU 主从架构  
**许可**: MIT
