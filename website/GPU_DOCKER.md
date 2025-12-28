# LeetGPU Website - GPU Docker 部署指南

本文档说明如何使用基于 CUDA 的 GPU Docker 镜像部署 LeetGPU 在线测试网站。

## 📋 基础镜像

使用内部 CUDA 预设镜像：
```
micr.cloud.mioffice.cn/cloudml-preset/cuda:12.8.1-py3.12-ubuntu22.04-0.1
```

**镜像特性**:
- CUDA 12.8.1
- Python 3.12
- Ubuntu 22.04
- 预装常用 ML/DL 库

## 🚀 快速开始

### 方式一：使用 GPU 构建脚本（推荐）

```bash
cd website
./build-gpu-image.sh
```

### 方式二：使用 Docker Compose

```bash
cd website
docker-compose -f docker-compose.gpu.yml up -d
```

### 方式三：手动构建

```bash
cd website

# 构建 GPU 生产版镜像
docker build -t leetgpu/website-gpu:latest -f Dockerfile.gpu.prod .

# 运行容器（需要 NVIDIA Docker）
docker run -d \
  --gpus all \
  -p 5000:5000 \
  --name leetgpu-website-gpu \
  leetgpu/website-gpu:latest
```

## 📦 可用的 Dockerfile

### 1. Dockerfile.gpu
- **用途**: GPU 开发版
- **特点**: 快速构建
- **推荐场景**: 开发和测试

### 2. Dockerfile.gpu.prod ⭐
- **用途**: GPU 生产版
- **特点**: 多阶段构建，优化大小
- **推荐场景**: 生产环境

## 🔧 前置要求

### 1. NVIDIA Docker 支持

```bash
# 安装 NVIDIA Docker
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# 验证安装
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

### 2. 基础镜像访问权限

确保可以访问内部镜像仓库：
```bash
# 登录内部仓库（如需要）
docker login micr.cloud.mioffice.cn

# 拉取基础镜像
docker pull micr.cloud.mioffice.cn/cloudml-preset/cuda:12.8.1-py3.12-ubuntu22.04-0.1
```

## 📋 构建步骤详解

### 步骤1：准备环境

```bash
cd website

# 确保元数据存在
python generate_challenge_metadata.py
```

### 步骤2：选择构建版本

#### 开发版（快速）
```bash
docker build -t leetgpu/website-gpu:dev -f Dockerfile.gpu .
```

#### 生产版（推荐）
```bash
docker build -t leetgpu/website-gpu:latest -f Dockerfile.gpu.prod .
```

### 步骤3：运行容器

```bash
# 基本运行
docker run -d \
  --gpus all \
  -p 5000:5000 \
  --name leetgpu-gpu \
  leetgpu/website-gpu:latest

# 挂载题目目录
docker run -d \
  --gpus all \
  -p 5000:5000 \
  -v $(pwd)/../challenges:/app/../challenges:ro \
  --name leetgpu-gpu \
  leetgpu/website-gpu:latest

# 指定 GPU
docker run -d \
  --gpus '"device=0,1"' \
  -p 5000:5000 \
  --name leetgpu-gpu \
  leetgpu/website-gpu:latest
```

## 🐳 Docker Compose 配置

### docker-compose.gpu.yml

```yaml
version: '3.8'

services:
  leetgpu-web-gpu:
    build:
      context: .
      dockerfile: Dockerfile.gpu.prod
    ports:
      - "5000:5000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    runtime: nvidia
    environment:
      - CUDA_VISIBLE_DEVICES=all
    restart: unless-stopped
```

### 使用 Compose

```bash
# 启动
docker-compose -f docker-compose.gpu.yml up -d

# 查看日志
docker-compose -f docker-compose.gpu.yml logs -f

# 停止
docker-compose -f docker-compose.gpu.yml down
```

## 🔍 验证 GPU 访问

### 检查容器内 GPU

```bash
# 查看 GPU 信息
docker exec leetgpu-gpu nvidia-smi

# 检查 CUDA 版本
docker exec leetgpu-gpu nvcc --version

# 测试 PyTorch GPU
docker exec leetgpu-gpu python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

## ⚙️ 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CUDA_VISIBLE_DEVICES` | `all` | 可见的 GPU 设备 |
| `FLASK_ENV` | `production` | Flask 环境 |
| `PYTHONUNBUFFERED` | `1` | Python 输出不缓冲 |
| `LD_LIBRARY_PATH` | `/usr/local/cuda/lib64:...` | CUDA 库路径 |

### 自定义环境变量

```bash
docker run -d \
  --gpus all \
  -p 5000:5000 \
  -e CUDA_VISIBLE_DEVICES="0,1" \
  -e FLASK_ENV=development \
  leetgpu/website-gpu:latest
```

## 📊 镜像大小对比

| 镜像 | 大小（预估） | 说明 |
|------|-------------|------|
| 基础 CUDA 镜像 | ~3GB | 包含 CUDA 12.8.1 |
| GPU 开发版 | ~3.2GB | 添加应用代码 |
| GPU 生产版 | ~3.1GB | 多阶段优化 |
| CPU 版本 | ~300MB | 无 CUDA 支持 |

## 🎯 使用场景

### 场景1：开发测试

```bash
# 使用开发版
docker build -t leetgpu/website-gpu:dev -f Dockerfile.gpu .
docker run -d --gpus all -p 5000:5000 leetgpu/website-gpu:dev
```

### 场景2：生产部署

```bash
# 使用生产版 + Compose
docker-compose -f docker-compose.gpu.yml up -d
```

### 场景3：多 GPU 环境

```bash
# 使用特定 GPU
docker run -d \
  --gpus '"device=0"' \
  -p 5000:5000 \
  --name leetgpu-gpu-0 \
  leetgpu/website-gpu:latest

docker run -d \
  --gpus '"device=1"' \
  -p 5001:5000 \
  --name leetgpu-gpu-1 \
  leetgpu/website-gpu:latest
```

### 场景4：GPU 资源限制

```bash
# 限制 GPU 内存
docker run -d \
  --gpus all \
  --shm-size=2g \
  -e CUDA_VISIBLE_DEVICES="0" \
  -p 5000:5000 \
  leetgpu/website-gpu:latest
```

## 🔧 故障排查

### 问题1: 无法访问 GPU

**症状**: `nvidia-smi` 命令失败

**解决**:
```bash
# 检查 NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi

# 重启 Docker
sudo systemctl restart docker
```

### 问题2: 基础镜像拉取失败

**症状**: 无法下载基础镜像

**解决**:
```bash
# 检查网络连接
ping micr.cloud.mioffice.cn

# 登录镜像仓库
docker login micr.cloud.mioffice.cn

# 手动拉取
docker pull micr.cloud.mioffice.cn/cloudml-preset/cuda:12.8.1-py3.12-ubuntu22.04-0.1
```

### 问题3: 容器启动失败

**症状**: 容器立即退出

**解决**:
```bash
# 查看日志
docker logs leetgpu-gpu

# 检查权限
ls -la challenges.json

# 重新生成元数据
python generate_challenge_metadata.py
```

### 问题4: 内存不足

**症状**: OOM 错误

**解决**:
```bash
# 增加共享内存
docker run -d \
  --gpus all \
  --shm-size=4g \
  -p 5000:5000 \
  leetgpu/website-gpu:latest
```

## 🔐 安全建议

1. **非 root 用户**: 生产版已配置为 leetgpu 用户运行
2. **只读挂载**: 题目目录使用 `:ro` 挂载
3. **GPU 隔离**: 使用 `CUDA_VISIBLE_DEVICES` 限制 GPU 访问
4. **资源限制**: 设置内存和 CPU 限制

```bash
docker run -d \
  --gpus '"device=0"' \
  --memory="4g" \
  --cpus="2.0" \
  --shm-size=2g \
  -p 5000:5000 \
  leetgpu/website-gpu:latest
```

## 📈 性能优化

### 1. 构建缓存

```bash
# 使用 BuildKit
DOCKER_BUILDKIT=1 docker build -f Dockerfile.gpu.prod -t leetgpu/website-gpu:latest .
```

### 2. 多阶段构建

生产版 Dockerfile 已使用多阶段构建优化镜像大小。

### 3. 层缓存

Dockerfile 已优化层顺序，频繁变化的文件放在后面。

## 📚 相关命令速查

```bash
# 构建
./build-gpu-image.sh                                    # 交互式构建
docker build -f Dockerfile.gpu.prod -t leetgpu/website-gpu:latest .

# 运行
docker run -d --gpus all -p 5000:5000 leetgpu/website-gpu:latest
docker-compose -f docker-compose.gpu.yml up -d

# 管理
docker ps | grep leetgpu                                # 查看容器
docker logs -f leetgpu-gpu                              # 查看日志
docker exec -it leetgpu-gpu /bin/bash                   # 进入容器
docker exec leetgpu-gpu nvidia-smi                      # 查看 GPU

# 清理
docker stop leetgpu-gpu && docker rm leetgpu-gpu        # 停止删除
docker rmi leetgpu/website-gpu:latest                   # 删除镜像
```

## 🎓 最佳实践

1. **使用生产版**: `Dockerfile.gpu.prod` 更安全更小
2. **资源限制**: 设置合理的 GPU、内存限制
3. **健康检查**: 启用健康检查监控服务状态
4. **日志管理**: 配置日志驱动和轮转
5. **定期更新**: 保持基础镜像和依赖更新

## 📞 支持

- 主文档: [README.md](README.md)
- Docker 文档: [DOCKER.md](DOCKER.md)
- 快速开始: [QUICK_START.md](QUICK_START.md)

---

© 2025 LeetGPU - GPU Programming Online Testing Platform
