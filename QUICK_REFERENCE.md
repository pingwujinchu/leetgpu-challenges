# 🚀 LeetGPU 主从架构 - 快速参考

## 📋 所有需求 ✅

1. ✅ 主从架构（主节点CPU，从节点GPU）
2. ✅ CUDA JIT封装（自动编译用户代码）
3. ✅ GPU资源监控（实时利用率、显存、温度）
4. ✅ 显存超90%排队
5. ✅ 消息队列通信（主节点推送，从节点拉取）
6. ✅ 跨机器分布式部署

## 🎯 快速开始

### 分布式部署（生产推荐）

**主节点 (192.168.1.100)**:
```bash
# 1. 配置Redis
sudo sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf
sudo systemctl restart redis
sudo ufw allow 6379,5000/tcp

# 2. 修改配置
cd /workspace/website
cp config_distributed.py config.py
# 编辑config.py修改实际IP

# 3. 启动主节点
python3 app.py
```

**GPU机器 (每台)**:
```bash
cd /workspace/website
python3 gpu_worker_mq.py \
    --id gpu-worker-X \
    --gpu 0 \
    --redis-host 192.168.1.100
```

### 本地测试
```bash
pip install redis
redis-server &
cd /workspace/website
./start_all_mq.sh
```

## 📚 关键文档

| 文档 | 用途 |
|------|------|
| `DISTRIBUTED_DEPLOYMENT.md` | 分布式部署完整指南 |
| `MESSAGE_QUEUE_ARCHITECTURE.md` | 消息队列架构说明 |
| `QUICK_START_MQ.md` | 快速开始 |
| `config_distributed.py` | 分布式配置模板 |

## 🔍 验证

```bash
# Redis连接测试
redis-cli -h 192.168.1.100 ping

# Worker状态
redis-cli -h 192.168.1.100 KEYS 'leetgpu:workers:status:*'

# 队列大小
redis-cli -h 192.168.1.100 LLEN leetgpu:tasks:queue
```

## 📂 关键文件

```
website/
├── config_distributed.py      # 分布式配置 ⭐
├── message_queue.py           # 消息队列
├── task_manager_mq.py         # 任务管理器(MQ)
├── gpu_worker_mq.py           # Worker(MQ)
├── start_worker_mq.sh         # Worker启动
└── deploy_example.sh          # 部署助手
```

## 🎯 三种模式

| 模式 | 命令 | 适用 |
|------|------|------|
| HTTP | `./start_all.sh` | 开发测试 |
| MQ本地 | `./start_all_mq.sh` | 功能验证 |
| MQ分布式 | 见上面 | 生产环境 |

## ✨ 核心特性

- 🔧 CUDA JIT自动编译
- 📊 实时GPU监控（5秒刷新）
- ⚡ 显存90%自动排队
- 🔄 Redis消息队列
- 🌐 跨机器部署
- 📈 自动负载均衡

## 📞 快速支持

```bash
# 部署助手
./deploy_example.sh

# 测试系统
python3 test_message_queue.py manager
```

---

**版本**: v2.1.0  
**状态**: ✅ 生产就绪

🎉 **所有功能完成！**
