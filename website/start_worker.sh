#!/bin/bash
# 启动GPU Worker节点

# 默认参数
WORKER_ID="gpu-worker-1"
PORT=5001
GPU_ID=0
HOST="0.0.0.0"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --id)
            WORKER_ID="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --gpu)
            GPU_ID="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --id <worker_id>    Worker ID (默认: gpu-worker-1)"
            echo "  --port <port>       监听端口 (默认: 5001)"
            echo "  --gpu <gpu_id>      GPU设备ID (默认: 0)"
            echo "  --host <host>       监听地址 (默认: 0.0.0.0)"
            echo "  --help              显示帮助信息"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

echo "======================================"
echo "启动 LeetGPU GPU Worker节点"
echo "======================================"
echo "Worker ID: $WORKER_ID"
echo "端口: $PORT"
echo "GPU设备: $GPU_ID"
echo "监听地址: $HOST"
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
echo "启动Worker节点..."
echo ""

python3 gpu_worker.py --id "$WORKER_ID" --port "$PORT" --gpu "$GPU_ID" --host "$HOST"
