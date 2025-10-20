# RocketMQ 消息队列快速开始

## 🚀 快速启动（3 步）

### 1. 启动 RocketMQ

使用 Docker Compose（最简单）:

```bash
# 创建 docker-compose-rocketmq.yml
cat > docker-compose-rocketmq.yml << 'EOF'
version: '3.8'
services:
  namesrv:
    image: apache/rocketmq:5.1.4
    container_name: rmqnamesrv
    ports:
      - 9876:9876
    command: sh mqnamesrv
    
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
    command: sh mqbroker
EOF

# 启动 RocketMQ
docker-compose -f docker-compose-rocketmq.yml up -d
```

### 2. 安装依赖

```bash
cd website
pip install -r requirements.txt
```

### 3. 启动服务

```bash
# 一键启动所有服务（主节点 + 3个 Worker）
./start_all_rocketmq.sh
```

或者分别启动:

```bash
# 启动主节点
python app.py --mode rocketmq

# 启动 Worker
./start_worker_rocketmq.sh gpu-worker-1 0 "RTX 4090"
```

## ✅ 验证

访问: http://localhost:5000

## 📝 配置

编辑 `website/config.py`:

```python
# RocketMQ配置
ROCKETMQ_NAMESERVER = 'localhost:9876'
ROCKETMQ_GROUP_ID = 'leetgpu_group'

# 消息队列选择
MESSAGE_QUEUE_TYPE = 'rocketmq'
```

## 🧪 测试

```bash
cd website
python test_rocketmq.py
```

## 📚 更多信息

查看完整文档: [ROCKETMQ_SETUP_GUIDE.md](ROCKETMQ_SETUP_GUIDE.md)

## ⚡ 核心特性

- ✅ **高性能**: RocketMQ 支持高吞吐量消息处理
- ✅ **GPU 路由**: 自动将任务路由到指定 GPU 型号
- ✅ **可靠性**: 消息持久化，确保任务不丢失
- ✅ **分布式**: 支持多节点部署
- ✅ **监控**: 实时查看任务和 Worker 状态

## 🔄 从 Redis 切换

只需修改配置:

```python
MESSAGE_QUEUE_TYPE = 'rocketmq'  # 从 'redis' 改为 'rocketmq'
```

代码无需修改! 🎉
