#!/bin/bash
# 启动主节点服务器

echo "======================================"
echo "启动 LeetGPU 主节点服务器"
echo "======================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
python3 -c "import flask" 2>/dev/null || {
    echo "安装依赖..."
    pip install -r requirements.txt
}

echo ""
echo "启动主节点..."
echo ""

python3 app.py
