# LeetGPU Website - Docker 文件说明

## 📋 Docker 相关文件总览

### 核心 Docker 文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `Dockerfile` | 768B | 开发版 Dockerfile，快速构建 |
| `Dockerfile.prod` | 1.8K | **生产版 Dockerfile**，多阶段构建，镜像更小更安全 |
| `docker-compose.yml` | 1.2K | Docker Compose 编排配置 |
| `.dockerignore` | - | Docker 构建忽略文件 |
| `.env.example` | - | 环境变量配置示例 |

### 脚本工具

| 脚本 | 大小 | 说明 |
|------|------|------|
| `build-image.sh` | 6.4K | **镜像构建脚本**（交互式，支持开发/生产版选择） |
| `push-image.sh` | 6.1K | **镜像推送脚本**（支持多平台仓库） |
| `docker-run.sh` | 2.0K | Docker 快速启动脚本 |
| `test-docker.sh` | 5.1K | Docker 测试套件 |
| `start.sh` | 1.4K | 本地快速启动脚本 |

### 辅助工具

| 文件 | 大小 | 说明 |
|------|------|------|
| `Makefile` | 4.0K | **常用命令快捷方式**，简化操作 |

### 文档

| 文档 | 说明 |
|------|------|
| `DOCKER.md` | Docker 完整部署指南（详细） |
| `QUICK_START.md` | 快速启动指南（精简） |
| `README.md` | 项目主文档 |

---

## 🎯 文件用途详解

### 1. Dockerfile vs Dockerfile.prod

#### Dockerfile（开发版）
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

**特点**:
- ✅ 构建快速
- ✅ 适合开发调试
- ❌ 镜像较大
- ❌ 以 root 运行

**使用场景**: 开发环境、快速测试

#### Dockerfile.prod（生产版）⭐
```dockerfile
# 阶段1: 构建
FROM python:3.11-slim as builder
...
# 阶段2: 运行
FROM python:3.11-slim
COPY --from=builder /opt/venv /opt/venv
...
```

**特点**:
- ✅ 多阶段构建，镜像更小
- ✅ 非 root 用户运行
- ✅ 包含健康检查
- ✅ 优化的层缓存
- ❌ 构建稍慢

**使用场景**: 生产环境、镜像分发

---

### 2. build-image.sh - 镜像构建脚本

**功能**:
- 交互式选择 Dockerfile
- 自定义版本号
- 自动生成元数据
- 构建后测试
- 镜像导出为 tar

**使用**:
```bash
./build-image.sh
```

**流程**:
1. 检查环境（Docker、文件）
2. 生成题目元数据
3. 选择构建类型（开发/生产）
4. 设置版本号
5. 构建镜像
6. 显示镜像信息
7. 可选测试运行
8. 可选导出 tar

---

### 3. push-image.sh - 镜像推送脚本

**支持的仓库**:
1. Docker Hub
2. 阿里云容器镜像服务
3. 腾讯云容器镜像服务
4. 华为云容器镜像服务
5. GitHub Container Registry
6. 自定义仓库

**功能**:
- 自动登录仓库
- 镜像标记
- 多版本推送
- 多架构构建（可选）

**使用**:
```bash
./push-image.sh
```

**示例输出**:
```
选择推送的仓库:
  1) Docker Hub
  2) 阿里云
  ...
请选择 [1-6]: 1

推送成功: latest
拉取镜像命令:
  docker pull leetgpu/website:latest
```

---

### 4. docker-run.sh - 快速启动脚本

**功能**:
- 自动检查环境
- 生成元数据（如需）
- 构建镜像
- 启动容器
- 显示日志

**使用**:
```bash
./docker-run.sh
```

---

### 5. test-docker.sh - 测试脚本

**测试项**:
1. ✅ Docker 环境检查
2. ✅ 必要文件检查
3. ✅ 题目元数据验证
4. ✅ 开发版镜像构建
5. ✅ 生产版镜像构建
6. ✅ 容器启动测试
7. ✅ 健康检查
8. ✅ API 端点测试
9. ✅ 主页加载测试
10. ✅ 容器日志检查

**使用**:
```bash
./test-docker.sh
```

**适用场景**: CI/CD、发布前验证

---

### 6. Makefile - 命令快捷方式

**常用命令**:

```bash
# 查看帮助
make help

# 开发相关
make install      # 安装依赖
make metadata     # 生成元数据
make dev          # 启动开发服务器

# Docker 构建
make build        # 开发版镜像
make build-prod   # 生产版镜像
make build-multi  # 多架构镜像

# Docker 运行
make run          # 运行容器
make run-dev      # 开发模式（挂载代码）
make stop         # 停止容器

# Docker Compose
make compose-up   # 启动
make compose-down # 停止
make compose-logs # 日志

# 维护
make clean        # 清理资源
make logs         # 查看日志
make shell        # 进入容器

# 一键操作
make deploy       # 元数据+构建+运行
make quick        # 快速开发
make quick-prod   # 快速生产
```

**示例**:
```bash
# 完整部署流程
make metadata     # 生成元数据
make build-prod   # 构建生产镜像
make run          # 运行容器
make logs         # 查看日志

# 或一键完成
make deploy
```

---

### 7. docker-compose.yml

**配置说明**:

```yaml
services:
  leetgpu-web:
    build: .                    # 构建配置
    ports: ["5000:5000"]        # 端口映射
    volumes:                    # 卷挂载
      - ../challenges:/app/../challenges:ro
    environment:                # 环境变量
      - FLASK_ENV=production
    restart: unless-stopped     # 重启策略
    healthcheck: ...           # 健康检查
```

**使用**:
```bash
# 启动
docker-compose up -d

# 查看
docker-compose ps
docker-compose logs -f

# 停止
docker-compose down
```

---

## 🚀 快速使用指南

### 场景1: 快速体验（新手）

```bash
cd website
make deploy
```

### 场景2: 开发调试

```bash
cd website
make dev
# 或
./start.sh
```

### 场景3: 生产部署

```bash
cd website
./build-image.sh      # 选择生产版
docker-compose up -d
```

### 场景4: 构建并推送镜像

```bash
cd website
./build-image.sh      # 构建
./push-image.sh       # 推送
```

### 场景5: CI/CD 集成

```bash
cd website
./test-docker.sh      # 运行测试
make build-prod       # 构建镜像
make push             # 推送镜像
```

---

## 📊 构建对比

| 特性 | Dockerfile | Dockerfile.prod |
|------|-----------|-----------------|
| 构建时间 | ~30秒 | ~45秒 |
| 镜像大小 | ~400MB | ~300MB |
| 构建方式 | 单阶段 | 多阶段 |
| 运行用户 | root | leetgpu (1000) |
| 健康检查 | ✅ | ✅ |
| 层优化 | 基础 | 优化 |
| 推荐场景 | 开发 | **生产** ⭐ |

---

## 🎯 最佳实践

### 1. 选择正确的 Dockerfile

- **开发**: 使用 `Dockerfile`
- **生产**: 使用 `Dockerfile.prod`

### 2. 使用脚本简化操作

```bash
# 而不是手动输入长命令
./build-image.sh

# 而不是
docker build -f Dockerfile.prod -t leetgpu/website:latest --build-arg ...
```

### 3. 使用 Makefile

```bash
make deploy    # 而不是多个命令
```

### 4. 环境变量管理

```bash
# 复制示例配置
cp .env.example .env

# 修改配置
vim .env

# 使用配置
docker-compose --env-file .env up
```

---

## 🔍 故障排查

### 问题: 构建失败

```bash
# 清理缓存
docker builder prune -a

# 重新构建
make build-prod
```

### 问题: 容器无法启动

```bash
# 查看日志
make logs

# 检查健康状态
make health
```

### 问题: 端口冲突

```bash
# 使用其他端口
docker run -d -p 8080:5000 leetgpu/website:latest
```

---

## 📚 相关文档

- **详细部署**: [DOCKER.md](DOCKER.md)
- **快速开始**: [QUICK_START.md](QUICK_START.md)
- **项目文档**: [README.md](README.md)
- **使用指南**: [../WEBSITE_GUIDE.md](../WEBSITE_GUIDE.md)

---

**总结**: 提供了完整的 Docker 生态系统，从开发到生产部署的全流程支持！🐳
