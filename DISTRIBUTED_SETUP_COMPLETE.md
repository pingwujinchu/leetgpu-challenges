# ✅ 分布式部署配置完成

## 🎯 用户需求确认

> "主节点和从节点是部署在不同机器上的。"

**已完成**: ✅ 支持跨机器分布式部署

## 📋 部署架构

```
主节点机器 (CPU)
  IP: 192.168.1.100
  ├── Flask Web (5000)
  ├── Redis (6379)
  └── TaskManager
       │
   (网络通信)
       │
  ┌────┼────┬─────────┐
  │    │    │         │
GPU机器1  GPU机器2  GPU机器3
.101      .102      .103
Worker1   Worker2   Worker3
4090      A100      H100
```

## 📦 新增内容

### 1. 分布式部署文档
- `DISTRIBUTED_DEPLOYMENT.md` (15KB)
  - 完整部署指南
  - 网络配置
  - 防火墙设置
  - 安全配置
  - 故障排查

### 2. 配置文件
- `config_distributed.py`
  - 分布式配置示例
  - 实际IP配置模板
  - 网络参数配置
  - 安全选项

### 3. 部署脚本
- `deploy_example.sh`
  - 交互式部署助手
  - 自动验证工具
  - 一键配置

### 4. 启动脚本更新
- `start_worker_mq.sh` - 支持远程Redis

## 🔧 配置步骤

### 主节点（192.168.1.100）

```bash
# 1. 配置Redis允许远程
sudo sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf
sudo systemctl restart redis

# 2. 开放端口
sudo ufw allow 6379/tcp
sudo ufw allow 5000/tcp

# 3. 修改config.py
REDIS_HOST = '192.168.1.100'  # 主节点IP

GPU_WORKERS = [
    {'host': '192.168.1.101', ...},  # GPU机器IP
    {'host': '192.168.1.102', ...},
    {'host': '192.168.1.103', ...}
]

# 4. 启动服务
python3 app.py
```

### GPU Worker机器（每台）

```bash
# GPU机器1 (192.168.1.101)
python3 gpu_worker_mq.py \
    --id gpu-worker-1 \
    --gpu 0 \
    --redis-host 192.168.1.100 \
    --redis-port 6379

# GPU机器2 (192.168.1.102)
python3 gpu_worker_mq.py \
    --id gpu-worker-2 \
    --gpu 0 \
    --redis-host 192.168.1.100

# GPU机器3 (192.168.1.103)
python3 gpu_worker_mq.py \
    --id gpu-worker-3 \
    --gpu 0 \
    --redis-host 192.168.1.100
```

## 🔍 验证部署

```bash
# 从任意GPU机器测试Redis连接
redis-cli -h 192.168.1.100 -p 6379 ping
# 应返回: PONG

# 查看在线Worker
redis-cli -h 192.168.1.100 KEYS 'leetgpu:workers:status:*'

# 查看队列
redis-cli -h 192.168.1.100 LLEN leetgpu:tasks:queue
```

## 🌐 网络要求

### 必要条件

1. **网络连通性**
   - 主节点 ↔ 所有GPU机器互通
   - 可以ping通

2. **端口开放**
   - 主节点Redis: 6379
   - 主节点Web: 5000
   - GPU机器: 无需开放端口（主动连接）

3. **防火墙规则**
   ```bash
   # 主节点
   sudo ufw allow from 192.168.1.0/24 to any port 6379
   sudo ufw allow 5000/tcp
   ```

### 推荐配置

- **内网部署**: 192.168.x.x 或 10.x.x.x
- **千兆网络**: 最低要求
- **万兆网络**: 大数据传输推荐
- **低延迟**: < 5ms

## 🔐 安全配置

### Redis密码

**主节点redis.conf**:
```bash
requirepass your_strong_password
```

**Worker启动时**:
```python
# 需要修改message_queue.py支持密码
mq = MessageQueue(
    host='192.168.1.100',
    password='your_strong_password'
)
```

### IP白名单

```bash
# Redis只允许特定IP
bind 192.168.1.100 192.168.1.101 192.168.1.102 192.168.1.103
```

### 防火墙限制

```bash
# 只允许GPU机器访问Redis
sudo ufw allow from 192.168.1.101 to any port 6379
sudo ufw allow from 192.168.1.102 to any port 6379
sudo ufw allow from 192.168.1.103 to any port 6379
sudo ufw deny 6379
```

## 📊 性能考虑

### 网络延迟

| 延迟 | 影响 | 建议 |
|------|------|------|
| < 1ms | 无影响 | 理想 |
| 1-5ms | 轻微影响 | 可接受 |
| 5-10ms | 中等影响 | 优化网络 |
| > 10ms | 明显影响 | 检查网络 |

### 带宽需求

- 任务数据: < 1MB/任务
- 结果数据: 可能较大
- 心跳数据: < 1KB/5秒
- 推荐带宽: 100Mbps+

## 🐛 常见问题

### Q1: Worker连不上Redis？

```bash
# 检查1: Redis是否监听0.0.0.0
sudo netstat -tlnp | grep 6379

# 检查2: 防火墙
sudo ufw status

# 检查3: 网络连通
ping 192.168.1.100
telnet 192.168.1.100 6379

# 检查4: Redis密码
redis-cli -h 192.168.1.100 -a password ping
```

### Q2: Worker在线但不拉取？

```bash
# GPU机器查看日志
tail -f logs/worker1_mq.log

# 主节点查看队列
redis-cli -h 192.168.1.100 LLEN leetgpu:tasks:queue

# 检查Worker心跳
redis-cli -h 192.168.1.100 GET leetgpu:workers:status:gpu-worker-1
```

### Q3: 性能不佳？

- 检查网络延迟: `ping -c 100 192.168.1.100`
- 检查带宽: `iperf3 -c 192.168.1.100`
- 优化Redis配置
- 使用更快的网络

## 📚 文档

| 文档 | 说明 |
|------|------|
| DISTRIBUTED_DEPLOYMENT.md | 完整部署指南 |
| config_distributed.py | 配置文件示例 |
| deploy_example.sh | 部署助手脚本 |

## 🎯 部署检查清单

### 主节点

- [ ] Redis已安装
- [ ] Redis配置bind 0.0.0.0
- [ ] Redis已重启
- [ ] 端口6379和5000已开放
- [ ] config.py中IP配置正确
- [ ] Flask应用启动成功

### GPU Worker（每台）

- [ ] Python环境已配置
- [ ] CUDA环境可用
- [ ] 依赖已安装
- [ ] 能ping通主节点
- [ ] Redis连接测试通过
- [ ] Worker启动成功

### 网络验证

- [ ] 主节点↔Worker网络连通
- [ ] Redis连接正常
- [ ] Worker心跳正常
- [ ] 任务能正常分发
- [ ] 结果能正常返回

## 🚀 快速部署

```bash
# === 主节点 ===
cd /workspace/website

# 1. 配置Redis
sudo sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf
sudo systemctl restart redis
sudo ufw allow 6379,5000/tcp

# 2. 修改config.py（使用config_distributed.py作为模板）
cp config_distributed.py config.py
# 编辑config.py，修改实际IP

# 3. 启动主节点
python3 app.py

# === GPU机器（每台）===
cd /workspace/website

# 1. 复制代码（或git clone）
scp -r user@192.168.1.100:/workspace/website .

# 2. 启动Worker
python3 gpu_worker_mq.py \
    --id gpu-worker-X \
    --gpu 0 \
    --redis-host 192.168.1.100
```

## ✅ 完成

分布式部署配置已完成：

✅ 支持跨机器部署  
✅ 完整部署文档  
✅ 配置文件模板  
✅ 网络配置指南  
✅ 安全配置建议  
✅ 故障排查方案  
✅ 性能优化建议  

---

**部署模式**: 分布式跨机器  
**通信方式**: Redis消息队列  
**网络要求**: 内网互通  
**状态**: ✅ 可用

🌐 **跨机器分布式部署已完全支持！**
