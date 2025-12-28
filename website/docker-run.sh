#!/bin/bash
# LeetGPU Website - Docker 快速启动脚本

echo "=========================================="
echo "  🐳 LeetGPU Docker 容器启动"
echo "=========================================="
echo ""

# 检查是否在 website 目录
if [ ! -f "app.py" ]; then
    echo "❌ 错误: 请在 website 目录中运行此脚本"
    exit 1
fi

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker 未安装"
    echo "请访问 https://www.docker.com/get-started 安装 Docker"
    exit 1
fi

# 检查 Docker Compose 是否可用
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ 错误: Docker Compose 未安装"
    exit 1
fi

# 生成题目元数据（如果不存在）
if [ ! -f "challenges.json" ]; then
    echo "📊 生成题目元数据..."
    python3 generate_challenge_metadata.py
    if [ $? -ne 0 ]; then
        echo "❌ 生成元数据失败"
        exit 1
    fi
    echo "✅ 元数据生成成功"
    echo ""
fi

# 检查使用 docker-compose 还是 docker compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# 构建并启动容器
echo "🔨 构建 Docker 镜像..."
$DOCKER_COMPOSE build

if [ $? -ne 0 ]; then
    echo "❌ 构建失败"
    exit 1
fi

echo ""
echo "🚀 启动容器..."
$DOCKER_COMPOSE up -d

if [ $? -ne 0 ]; then
    echo "❌ 启动失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "  ✅ 容器启动成功！"
echo "=========================================="
echo ""
echo "📍 访问地址: http://localhost:5000"
echo ""
echo "🔧 管理命令:"
echo "  查看日志: $DOCKER_COMPOSE logs -f"
echo "  停止容器: $DOCKER_COMPOSE stop"
echo "  重启容器: $DOCKER_COMPOSE restart"
echo "  删除容器: $DOCKER_COMPOSE down"
echo ""
echo "按 Ctrl+C 查看日志，或直接访问网站"
echo ""

# 显示日志
$DOCKER_COMPOSE logs -f
