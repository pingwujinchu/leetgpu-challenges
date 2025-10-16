#!/bin/bash
# 启动GPU Worker节点（消息队列版本）
# 支持跨机器部署

# 默认参数
WORKER_ID="gpu-worker-1"
GPU_ID=0
REDIS_HOST="localhost"  # 生产环境改为主节点IP，如: 192.168.1.100
REDIS_PORT=6379
REDIS_DB=0

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --id)
            WORKER_ID="$2"
            shift 2
            ;;
        --gpu)
            GPU_ID="$2"
            shift 2
            ;;
        --redis-host)
            REDIS_HOST="$2"
            shift 2
            ;;
        --redis-port)
            REDIS_PORT="$2"
            shift 2
            ;;
        --redis-db)
            REDIS_DB="$2"
            shift 2
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --id <worker_id>        Worker ID (默认: gpu-worker-1)"
            echo "  --gpu <gpu_id>          GPU设备ID (默认: 0)"
            echo "  --redis-host <host>     Redis主机 (默认: localhost)"
            echo "  --redis-port <port>     Redis端口 (默认: 6379)"
            echo "  --redis-db <db>         Redis数据库 (默认: 0)"
            echo "  --help                  显示帮助信息"
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
echo "（消息队列模式）"
echo "======================================"
echo "Worker ID: $WORKER_ID"
echo "GPU设备: $GPU_ID"
echo "Redis: $REDIS_HOST:$REDIS_PORT/$REDIS_DB"
echo "======================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
python3 -c "import redis" 2>/dev/null || {
    echo "安装依赖..."
    pip install -r requirements.txt
}

echo ""
echo "启动Worker节点..."
echo ""

python3 gpu_worker_mq.py \
    --id "$WORKER_ID" \
    --gpu "$GPU_ID" \
    --redis-host "$REDIS_HOST" \
    --redis-port "$REDIS_PORT" \
    --redis-db "$REDIS_DB"
