# LeetGPU Website - Docker 部署指南

本文档提供了 LeetGPU 在线测试网站的 Docker 部署完整指南。

## 📋 目录

- [快速开始](#快速开始)
- [构建镜像](#构建镜像)
- [运行容器](#运行容器)
- [Docker Compose](#docker-compose)
- [推送镜像](#推送镜像)
- [Makefile 命令](#makefile-命令)
- [多架构支持](#多架构支持)
- [常见问题](#常见问题)

## 🚀 快速开始

### 方法一：使用脚本（推荐新手）

```bash
cd website

# 构建镜像
./build-image.sh

# 运行容器
./docker-run.sh
```

### 方法二：使用 Makefile（推荐开发者）

```bash
cd website

# 一键部署
make deploy

# 或分步执行
make metadata      # 生成题目元数据
make build-prod    # 构建生产镜像
make run           # 运行容器
```

### 方法三：使用 Docker Compose

```bash
cd website
docker-compose up -d
```

### 方法四：直接使用 Docker 命令

```bash
cd website

# 构建
docker build -t leetgpu/website:latest -f Dockerfile.prod .

# 运行
docker run -d -p 5000:5000 --name leetgpu-website leetgpu/website:latest
```

## 🔨 构建镜像

### 开发版镜像

```bash
# 使用脚本（交互式）
./build-image.sh

# 使用 Makefile
make build

# 使用 Docker 命令
docker build -t leetgpu/website:dev -f Dockerfile .
```

### 生产版镜像（推荐）

生产版使用多阶段构建，镜像更小，更安全。

```bash
# 使用脚本
./build-image.sh  # 选择选项 2

# 使用 Makefile
make build-prod

# 使用 Docker 命令
docker build -t leetgpu/website:latest -f Dockerfile.prod .
```

### 构建特定版本

```bash
# 设置版本号
export VERSION=1.0.0

# 构建
docker build -t leetgpu/website:1.0.0 -f Dockerfile.prod .

# 或使用脚本（会提示输入版本）
./build-image.sh
```

## 🏃 运行容器

### 基本运行

```bash
docker run -d \
  --name leetgpu-website \
  -p 5000:5000 \
  leetgpu/website:latest
```

访问 `http://localhost:5000`

### 自定义端口

```bash
docker run -d \
  --name leetgpu-website \
  -p 8080:5000 \
  leetgpu/website:latest
```

访问 `http://localhost:8080`

### 挂载题目目录

```bash
docker run -d \
  --name leetgpu-website \
  -p 5000:5000 \
  -v $(pwd)/../challenges:/app/../challenges:ro \
  leetgpu/website:latest
```

### 环境变量配置

```bash
docker run -d \
  --name leetgpu-website \
  -p 5000:5000 \
  -e FLASK_ENV=production \
  -e PYTHONUNBUFFERED=1 \
  leetgpu/website:latest
```

### 查看日志

```bash
# 实时查看
docker logs -f leetgpu-website

# 查看最后 100 行
docker logs --tail 100 leetgpu-website
```

### 进入容器

```bash
docker exec -it leetgpu-website /bin/bash
```

### 停止和删除

```bash
# 停止
docker stop leetgpu-website

# 删除
docker rm leetgpu-website

# 强制删除运行中的容器
docker rm -f leetgpu-website
```

## 📦 Docker Compose

### 启动服务

```bash
# 后台运行
docker-compose up -d

# 前台运行（查看日志）
docker-compose up

# 指定配置文件
docker-compose -f docker-compose.yml up -d
```

### 管理服务

```bash
# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose stop

# 停止并删除
docker-compose down

# 重启服务
docker-compose restart
```

### docker-compose.yml 配置说明

```yaml
version: '3.8'

services:
  leetgpu-web:
    build:
      context: .
      dockerfile: Dockerfile.prod    # 使用生产版
    ports:
      - "5000:5000"                 # 端口映射
    volumes:
      - ../challenges:/app/../challenges:ro  # 挂载题目（只读）
    environment:
      - FLASK_ENV=production        # 环境变量
    restart: unless-stopped         # 自动重启
    healthcheck:                    # 健康检查
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/stats"]
      interval: 30s
      timeout: 3s
      retries: 3
```

## 📤 推送镜像

### 使用推送脚本

```bash
./push-image.sh
```

脚本支持：
- Docker Hub
- 阿里云容器镜像服务
- 腾讯云容器镜像服务
- 华为云容器镜像服务
- GitHub Container Registry
- 自定义仓库

### Docker Hub

```bash
# 登录
docker login

# 标记镜像
docker tag leetgpu/website:latest yourusername/leetgpu-website:latest

# 推送
docker push yourusername/leetgpu-website:latest
```

### 阿里云

```bash
# 登录
docker login --username=your_username registry.cn-hangzhou.aliyuncs.com

# 标记
docker tag leetgpu/website:latest registry.cn-hangzhou.aliyuncs.com/namespace/website:latest

# 推送
docker push registry.cn-hangzhou.aliyuncs.com/namespace/website:latest
```

### GitHub Container Registry

```bash
# 使用 Personal Access Token 登录
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# 标记
docker tag leetgpu/website:latest ghcr.io/username/leetgpu-website:latest

# 推送
docker push ghcr.io/username/leetgpu-website:latest
```

## 🛠️ Makefile 命令

查看所有可用命令：

```bash
make help
```

### 常用命令

| 命令 | 说明 |
|------|------|
| `make install` | 安装 Python 依赖 |
| `make metadata` | 生成题目元数据 |
| `make dev` | 启动开发服务器 |
| `make build` | 构建开发版镜像 |
| `make build-prod` | 构建生产版镜像 |
| `make run` | 运行容器 |
| `make stop` | 停止容器 |
| `make clean` | 清理容器和镜像 |
| `make logs` | 查看日志 |
| `make shell` | 进入容器 Shell |
| `make deploy` | 一键部署 |

### 完整工作流示例

```bash
# 开发环境
make metadata     # 生成元数据
make dev          # 启动开发服务器

# 生产部署
make build-prod   # 构建生产镜像
make run          # 运行容器
make logs         # 查看日志

# 清理
make stop         # 停止容器
make clean        # 清理资源
```

## 🌍 多架构支持

### 构建多架构镜像

需要 Docker Buildx：

```bash
# 创建 builder
docker buildx create --name leetgpu-builder --use

# 构建并推送多架构镜像
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t leetgpu/website:latest \
  -f Dockerfile.prod \
  --push \
  .
```

或使用 Makefile：

```bash
make build-multi
```

### 支持的架构

- `linux/amd64` - x86_64 架构（Intel/AMD）
- `linux/arm64` - ARM64 架构（Apple Silicon, ARM 服务器）

## 💾 镜像管理

### 导出镜像

```bash
# 使用 Makefile
make save

# 使用 Docker 命令
docker save leetgpu/website:latest | gzip > leetgpu-website.tar.gz
```

### 加载镜像

```bash
# 使用 Makefile
make load

# 使用 Docker 命令
docker load < leetgpu-website.tar.gz
```

### 查看镜像信息

```bash
# 列出镜像
docker images | grep leetgpu

# 查看详细信息
docker inspect leetgpu/website:latest

# 查看历史
docker history leetgpu/website:latest
```

## 🔍 健康检查

容器内置健康检查：

```bash
# 查看健康状态
docker inspect --format='{{.State.Health.Status}}' leetgpu-website

# 使用 Makefile
make health
```

健康检查配置：
- 检查间隔：30秒
- 超时时间：3秒
- 重试次数：3次
- 启动等待：10秒

## 📊 监控和日志

### 查看资源使用

```bash
# 实时统计
docker stats leetgpu-website

# 使用 Makefile
make stats
```

### 日志管理

```bash
# 实时日志
docker logs -f leetgpu-website

# 最近日志
docker logs --tail 100 leetgpu-website

# 带时间戳
docker logs -t leetgpu-website

# 使用 Makefile
make logs
```

## 🔧 常见问题

### 1. 端口已被占用

```bash
# 查看占用 5000 端口的进程
lsof -i :5000

# 或使用其他端口
docker run -d -p 8080:5000 leetgpu/website:latest
```

### 2. 镜像构建失败

```bash
# 清理构建缓存
docker builder prune -a

# 重新构建
docker build --no-cache -t leetgpu/website:latest -f Dockerfile.prod .
```

### 3. 容器无法访问题目文件

```bash
# 确保挂载路径正确
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/../challenges:/app/../challenges:ro \
  leetgpu/website:latest
```

### 4. 容器启动后立即退出

```bash
# 查看日志
docker logs leetgpu-website

# 查看退出码
docker inspect leetgpu-website --format='{{.State.ExitCode}}'
```

### 5. 内存不足

```bash
# 限制内存使用
docker run -d \
  -p 5000:5000 \
  --memory="512m" \
  --memory-swap="1g" \
  leetgpu/website:latest
```

## 🔐 安全建议

1. **使用非 root 用户**：生产版 Dockerfile 已配置
2. **只读挂载**：题目目录使用 `:ro` 只读挂载
3. **网络隔离**：使用自定义网络
4. **定期更新**：保持基础镜像和依赖更新
5. **扫描漏洞**：使用 `docker scan` 检查

```bash
# 扫描镜像漏洞
docker scan leetgpu/website:latest
```

## 📝 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `FLASK_ENV` | Flask 环境 | `production` |
| `FLASK_APP` | Flask 应用入口 | `app.py` |
| `PYTHONUNBUFFERED` | Python 输出缓冲 | `1` |

## 🎯 生产部署建议

1. **使用反向代理**（Nginx/Traefik）
2. **启用 HTTPS**
3. **配置日志轮转**
4. **设置资源限制**
5. **使用容器编排**（Kubernetes/Docker Swarm）
6. **配置监控告警**

## 📞 支持

如有问题，请查看：
- 主文档：`README.md`
- 使用指南：`WEBSITE_GUIDE.md`
- 官网：https://leetgpu.com

---

© 2025 LeetGPU - GPU Programming Online Testing Platform
