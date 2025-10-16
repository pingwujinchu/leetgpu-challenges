#!/bin/bash
# 在GPU服务器上启动多个Worker（一GPU一Worker）
# 自动检测GPU型号，每个Worker只拉取对应型号的任务

# 配置
REDIS_HOST="${REDIS_HOST:-192.168.1.100}"
SERVER_NAME=$(hostname)

# 检测GPU数量
if command -v nvidia-smi &> /dev/null; then
    NUM_GPUS=$(nvidia-smi --list-gpus | wc -l)
else
    echo "错误: 未找到nvidia-smi命令"
    echo "请确保NVIDIA驱动已安装"
    exit 1
fi

echo "======================================"
echo "启动多GPU Worker（GPU型号路由）"
echo "======================================"
echo "服务器: $SERVER_NAME"
echo "GPU数量: $NUM_GPUS"
echo "Redis: $REDIS_HOST"
echo "======================================"
echo ""

if [ $NUM_GPUS -eq 0 ]; then
    echo "错误: 未检测到GPU"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 启动每个GPU的Worker
for gpu_id in $(seq 0 $((NUM_GPUS-1))); do
    worker_id="$SERVER_NAME-gpu-$gpu_id"
    
    # 获取GPU型号
    gpu_name=$(nvidia-smi -i $gpu_id --query-gpu=name --format=csv,noheader,nounits)
    
    # 清理GPU名称（去除前后空格）
    gpu_name=$(echo "$gpu_name" | xargs)
    
    echo "启动 Worker: $worker_id"
    echo "  GPU ID: $gpu_id"
    echo "  GPU型号: $gpu_name"
    
    # 使用CUDA_VISIBLE_DEVICES确保GPU隔离
    # Worker会只拉取匹配此GPU型号的任务
    CUDA_VISIBLE_DEVICES=$gpu_id python3 gpu_worker_mq.py \
        --id "$worker_id" \
        --gpu 0 \
        --gpu-model "$gpu_name" \
        --redis-host $REDIS_HOST \
        > logs/worker-$worker_id.log 2>&1 &
    
    pid=$!
    echo "  PID: $pid"
    echo "  日志: logs/worker-$worker_id.log"
    echo "  队列: leetgpu:tasks:queue:$gpu_name"
    echo ""
    
    sleep 1
done

echo ""
echo "======================================"
echo "所有Worker已启动"
echo "======================================"
echo ""
echo "查看GPU状态:"
echo "  nvidia-smi"
echo ""
echo "查看日志:"
echo "  tail -f logs/worker-*.log"
echo ""
echo "查看进程:"
echo "  ps aux | grep gpu_worker_mq"
echo ""
echo "停止所有Worker:"
echo "  pkill -f gpu_worker_mq"
echo ""
