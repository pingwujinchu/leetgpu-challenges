#!/bin/bash
# LeetGPU Website Quick Start Script

echo "=========================================="
echo "  🚀 LeetGPU 在线测试网站启动脚本"
echo "=========================================="
echo ""

# Check if we're in the website directory
if [ ! -f "app.py" ]; then
    echo "❌ 错误: 请在 website 目录中运行此脚本"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: Python 3 未安装"
    exit 1
fi

# Check if challenges.json exists
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

# Check if Flask is installed
if ! python3 -c "import flask" &> /dev/null; then
    echo "📦 安装依赖..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
    echo "✅ 依赖安装成功"
    echo ""
fi

# Start the server
echo "=========================================="
echo "  🌐 启动Web服务器..."
echo "=========================================="
echo ""
echo "访问地址: http://localhost:5000"
echo "按 Ctrl+C 停止服务器"
echo ""

python3 app.py
