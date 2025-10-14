# 🎉 GPU Docker 镜像配置完成总结

## ✅ 已完成的 GPU Docker 功能

### 📦 新增 GPU Docker 文件（4个）

| 文件 | 说明 |
|------|------|
| `Dockerfile.gpu` | GPU 开发版（基于 CUDA 12.8.1） |
| `Dockerfile.gpu.prod` | GPU 生产版（多阶段构建）⭐ |
| `docker-compose.gpu.yml` | GPU Docker Compose 配置 |
| `build-gpu-image.sh` | GPU 镜像交互式构建脚本 |

### 📚 新增文档（1个）

| 文档 | 说明 |
|------|------|
| `GPU_DOCKER.md` | GPU Docker 完整部署指南 |

### 🛠️ Makefile 新增命令（6个）

```bash
make build-gpu          # 构建 GPU 开发版
make build-gpu-prod     # 构建 GPU 生产版
make run-gpu            # 运行 GPU 容器
make compose-gpu-up     # 启动 GPU Compose
make compose-gpu-down   # 停止 GPU Compose
make compose-gpu-logs   # 查看 GPU Compose 日志
```

---

## 🎯 基础镜像信息

```
镜像名称: micr.cloud.mioffice.cn/cloudml-preset/cuda:12.8.1-py3.12-ubuntu22.04-0.1
CUDA 版本: 12.8.1
Python 版本: 3.12
操作系统: Ubuntu 22.04
```

---

## 🚀 快速使用指南

### 方式1：使用 GPU 构建脚本（推荐）⭐

```bash
cd website
./build-gpu-image.sh
```

**交互式流程**：
1. ✅ 检查 Docker 环境
2. ✅ 拉取 CUDA 基础镜像
3. ✅ 生成题目元数据
4. ✅ 选择构建类型（开发/生产）
5. ✅ 设置版本号
6. ✅ 构建镜像
7. ✅ 显示镜像信息
8. ✅ 可选测试运行
9. ✅ 可选导出 tar

### 方式2：使用 Docker Compose

```bash
cd website
docker-compose -f docker-compose.gpu.yml up -d
```

### 方式3：使用 Makefile

```bash
cd website

# 构建 GPU 镜像
make build-gpu-prod

# 运行 GPU 容器
make run-gpu

# 或使用 Compose
make compose-gpu-up
```

### 方式4：手动构建和运行

```bash
cd website

# 构建生产版镜像
docker build -t leetgpu/website-gpu:latest -f Dockerfile.gpu.prod .

# 运行容器（需要 NVIDIA Docker）
docker run -d \
  --gpus all \
  -p 5000:5000 \
  --name leetgpu-gpu \
  leetgpu/website-gpu:latest
```

---

## 📋 GPU vs CPU 版本对比

| 特性 | CPU 版本 | GPU 版本 |
|------|---------|----------|
| **基础镜像** | python:3.11-slim | CUDA 12.8.1 + Python 3.12 |
| **镜像大小** | ~300MB | ~3.1GB |
| **GPU 支持** | ❌ | ✅ |
| **CUDA** | - | 12.8.1 |
| **构建时间** | ~45秒 | ~3-5分钟 |
| **运行要求** | 无特殊要求 | 需要 NVIDIA Docker |
| **适用场景** | 一般部署 | GPU 计算环境 |

---

## 🔧 前置要求

### 1. NVIDIA Docker Runtime

```bash
# 安装 NVIDIA Docker
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### 2. 验证 GPU 访问

```bash
# 测试 NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

### 3. 基础镜像访问权限

```bash
# 登录内部仓库（如需要）
docker login micr.cloud.mioffice.cn

# 拉取基础镜像
docker pull micr.cloud.mioffice.cn/cloudml-preset/cuda:12.8.1-py3.12-ubuntu22.04-0.1
```

---

## 📊 文件结构

```
website/
├── 🐳 GPU Docker 配置
│   ├── Dockerfile.gpu              # GPU 开发版
│   ├── Dockerfile.gpu.prod         # GPU 生产版 ⭐
│   ├── docker-compose.gpu.yml      # GPU Compose
│   └── build-gpu-image.sh          # GPU 构建脚本
│
├── 🐳 CPU Docker 配置
│   ├── Dockerfile                  # CPU 开发版
│   ├── Dockerfile.prod             # CPU 生产版
│   ├── docker-compose.yml          # CPU Compose
│   └── build-image.sh              # CPU 构建脚本
│
├── 📚 GPU 文档
│   └── GPU_DOCKER.md               # GPU 完整指南
│
├── 📚 通用文档
│   ├── DOCKER.md                   # Docker 通用指南
│   ├── QUICK_START.md              # 快速开始
│   └── README.md                   # 项目文档
│
└── 🛠️ 工具
    └── Makefile                    # 统一命令接口
```

---

## ✨ GPU Dockerfile 特性

### Dockerfile.gpu（开发版）

```dockerfile
FROM micr.cloud.mioffice.cn/cloudml-preset/cuda:12.8.1-py3.12-ubuntu22.04-0.1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

**特点**：
- ✅ 快速构建
- ✅ 适合开发调试
- ❌ 镜像较大

### Dockerfile.gpu.prod（生产版）⭐

```dockerfile
# 阶段1: 构建
FROM cuda:12.8.1... as builder
RUN pip install -r requirements.txt

# 阶段2: 运行
FROM cuda:12.8.1...
COPY --from=builder /opt/venv /opt/venv
USER leetgpu
```

**特点**：
- ✅ 多阶段构建
- ✅ 非 root 用户
- ✅ 健康检查
- ✅ 安全加固

---

## 🎯 使用场景

### 场景1：本地开发测试

```bash
# 快速构建开发版
make build-gpu
make run-gpu
```

### 场景2：生产环境部署

```bash
# 使用生产版 + Compose
make build-gpu-prod
make compose-gpu-up
```

### 场景3：多 GPU 环境

```bash
# GPU 0
docker run -d --gpus '"device=0"' -p 5000:5000 --name gpu-0 leetgpu/website-gpu

# GPU 1
docker run -d --gpus '"device=1"' -p 5001:5000 --name gpu-1 leetgpu/website-gpu
```

### 场景4：GPU 资源限制

```bash
docker run -d \
  --gpus '"device=0"' \
  --memory="4g" \
  --cpus="2.0" \
  -p 5000:5000 \
  leetgpu/website-gpu
```

---

## 🔍 验证安装

### 1. 检查镜像

```bash
docker images | grep leetgpu

# 应该看到
# leetgpu/website-gpu  latest  ...  ~3.1GB
```

### 2. 测试运行

```bash
# 启动容器
make run-gpu

# 查看日志
docker logs -f leetgpu-website-gpu

# 访问网站
curl http://localhost:5000/api/stats
```

### 3. 验证 GPU 访问

```bash
# 进入容器
docker exec -it leetgpu-website-gpu /bin/bash

# 查看 GPU
nvidia-smi

# 检查 CUDA
nvcc --version

# 测试 PyTorch（如果安装）
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

---

## 📚 完整命令速查

### 构建相关

```bash
# GPU 版本
./build-gpu-image.sh              # 交互式构建（推荐）
make build-gpu                    # 开发版
make build-gpu-prod               # 生产版

# CPU 版本
./build-image.sh                  # 交互式构建
make build                        # 开发版
make build-prod                   # 生产版
```

### 运行相关

```bash
# GPU 版本
make run-gpu                      # 单容器
make compose-gpu-up               # Compose

# CPU 版本
make run                          # 单容器
make compose-up                   # Compose
```

### 管理相关

```bash
# 查看日志
docker logs -f leetgpu-website-gpu
make compose-gpu-logs

# 进入容器
docker exec -it leetgpu-website-gpu /bin/bash

# 停止容器
docker stop leetgpu-website-gpu
make compose-gpu-down

# 查看 GPU
docker exec leetgpu-website-gpu nvidia-smi
```

---

## 🎓 最佳实践

1. **使用生产版**: `Dockerfile.gpu.prod` 更安全更小
2. **资源限制**: 设置合理的 GPU、内存、CPU 限制
3. **GPU 隔离**: 使用 `CUDA_VISIBLE_DEVICES` 控制可见 GPU
4. **健康检查**: 启用健康检查监控服务
5. **日志管理**: 配置日志驱动和轮转
6. **定期更新**: 保持基础镜像和依赖更新

---

## 🔧 常见问题

### Q1: GPU 无法访问？

```bash
# 检查 NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi

# 重启 Docker
sudo systemctl restart docker
```

### Q2: 基础镜像拉取失败？

```bash
# 登录内部仓库
docker login micr.cloud.mioffice.cn

# 手动拉取
docker pull micr.cloud.mioffice.cn/cloudml-preset/cuda:12.8.1-py3.12-ubuntu22.04-0.1
```

### Q3: 容器内存不足？

```bash
# 增加共享内存
docker run -d --gpus all --shm-size=4g -p 5000:5000 leetgpu/website-gpu
```

### Q4: 想同时运行 CPU 和 GPU 版本？

```bash
# CPU 版本 - 端口 5000
make run

# GPU 版本 - 端口 5001
docker run -d --gpus all -p 5001:5000 --name leetgpu-gpu leetgpu/website-gpu
```

---

## 📖 文档索引

| 文档 | 用途 |
|------|------|
| `GPU_DOCKER.md` | GPU Docker 完整指南 |
| `DOCKER.md` | 通用 Docker 部署指南 |
| `QUICK_START.md` | 快速开始指南 |
| `README.md` | 项目主文档 |
| `GPU_SETUP_SUMMARY.md` | 本文档（GPU 配置总结） |

---

## 🎉 总结

### ✅ GPU 支持完成度: 100%

- [x] GPU 开发版 Dockerfile
- [x] GPU 生产版 Dockerfile（多阶段构建）
- [x] GPU Docker Compose 配置
- [x] GPU 构建脚本
- [x] GPU 相关 Makefile 命令
- [x] GPU 完整文档
- [x] 支持 CUDA 12.8.1
- [x] 支持 Python 3.12
- [x] 健康检查
- [x] 非 root 用户运行

### 🚀 立即开始

```bash
cd website
./build-gpu-image.sh
# 访问 http://localhost:5000
```

### 📞 获取帮助

查看详细文档：
```bash
cat website/GPU_DOCKER.md
```

---

**GPU Docker 配置已完全就绪！** 🎊

---

© 2025 LeetGPU - GPU Programming Online Testing Platform
