# LeetGPU 网站快速启动指南

## 🎯 选择你的启动方式

### 1. 💻 我只想快速体验 → 使用 Docker（最简单）

```bash
cd website
make deploy
```

就这么简单！打开浏览器访问 `http://localhost:5000`

---

### 2. 🐳 Docker 详细选项

#### 选项 A：一键部署（推荐）
```bash
cd website
make deploy
# 或
./docker-run.sh
```

#### 选项 B：Docker Compose
```bash
cd website
docker-compose up -d
```

#### 选项 C：手动构建
```bash
cd website
./build-image.sh              # 构建镜像（交互式）
docker run -d -p 5000:5000 --name leetgpu-website leetgpu/website:latest
```

#### 选项 D：Makefile 命令
```bash
make build-prod    # 构建生产版镜像
make run           # 运行容器
make logs          # 查看日志
```

**查看完整 Docker 文档**: [DOCKER.md](DOCKER.md)

---

### 3. 🔧 本地开发环境

适合需要修改代码的开发者。

```bash
cd website

# 快速启动
./start.sh

# 或使用 Makefile
make dev
```

手动步骤：
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 生成元数据
python generate_challenge_metadata.py

# 3. 启动服务器
python app.py
```

---

## 📋 所有启动脚本对比

| 脚本 | 用途 | 环境 | 推荐场景 |
|------|------|------|----------|
| `make deploy` | 一键部署 | Docker | ⭐ 生产环境 |
| `./docker-run.sh` | Docker快速启动 | Docker | 快速测试 |
| `docker-compose up` | Compose部署 | Docker | 多容器编排 |
| `./start.sh` | 本地快速启动 | 本地 | 开发调试 |
| `make dev` | 开发模式 | 本地 | 开发环境 |
| `./build-image.sh` | 构建镜像 | Docker | 自定义构建 |
| `./push-image.sh` | 推送镜像 | Docker | 发布镜像 |
| `./test-docker.sh` | 测试Docker | Docker | CI/CD |

---

## 🛠️ Makefile 常用命令

查看所有命令：
```bash
make help
```

常用命令：

### 开发相关
```bash
make dev          # 启动开发服务器
make metadata     # 生成题目元数据
make install      # 安装依赖
```

### Docker 相关
```bash
make build        # 构建开发版镜像
make build-prod   # 构建生产版镜像（推荐）
make run          # 运行容器
make stop         # 停止容器
make logs         # 查看日志
make shell        # 进入容器
```

### 部署相关
```bash
make deploy       # 一键部署（元数据+构建+运行）
make clean        # 清理容器和镜像
make push         # 推送镜像
```

### Docker Compose
```bash
make compose-up   # 启动 compose
make compose-down # 停止 compose
make compose-logs # 查看 compose 日志
```

---

## 🔍 验证安装

访问以下地址测试：

- **主页**: http://localhost:5000
- **测验**: http://localhost:5000/quiz
- **API统计**: http://localhost:5000/api/stats
- **题目列表**: http://localhost:5000/api/challenges

---

## 🚨 常见问题

### 端口 5000 被占用？

**Docker方式**：
```bash
docker run -d -p 8080:5000 --name leetgpu-website leetgpu/website:latest
```
访问 `http://localhost:8080`

**本地方式**：
修改 `app.py` 最后一行：
```python
app.run(debug=True, host='0.0.0.0', port=8080)
```

### Docker 镜像构建失败？

```bash
# 清理缓存重新构建
docker builder prune -a
make build-prod
```

### 找不到题目？

```bash
# 重新生成元数据
python generate_challenge_metadata.py
# 或
make metadata
```

### 容器无法访问？

```bash
# 查看日志
docker logs leetgpu-website
# 或
make logs

# 检查健康状态
make health
```

---

## 📖 更多文档

- **完整使用指南**: [WEBSITE_GUIDE.md](../WEBSITE_GUIDE.md)
- **Docker详细文档**: [DOCKER.md](DOCKER.md)
- **项目README**: [README.md](README.md)
- **贡献指南**: [../CONTRIBUTING.md](../CONTRIBUTING.md)

---

## 🎉 开始使用

选择上面任意一种方式启动后：

1. 打开浏览器访问 `http://localhost:5000`
2. 选择你的 GPU 型号（可选）
3. 浏览 54 道 GPU 编程题目
4. 开始测验或学习

祝你学习愉快！🚀
