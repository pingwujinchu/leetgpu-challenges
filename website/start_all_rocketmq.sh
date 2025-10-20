#!/bin/bash

# 启动所有服务的脚本 (RocketMQ版本)

NAMESERVER=${1:-"localhost:9876"}

echo "========================================="
echo "启动所有服务 (RocketMQ模式)"
echo "========================================="
echo "NameServer: $NAMESERVER"
echo "========================================="

# 启动主节点
echo ""
echo "启动主节点..."
python app.py --mode rocketmq &
MASTER_PID=$!
echo "主节点 PID: $MASTER_PID"

# 等待主节点启动
sleep 3

# 启动Worker 1 (RTX 4090)
echo ""
echo "启动Worker 1 (RTX 4090)..."
python gpu_worker_rocketmq.py \
    --id "gpu-worker-1" \
    --gpu 0 \
    --gpu-model "RTX 4090" \
    --nameserver "$NAMESERVER" \
    --group-id "leetgpu_group" &
WORKER1_PID=$!
echo "Worker 1 PID: $WORKER1_PID"

# 启动Worker 2 (A100)
echo ""
echo "启动Worker 2 (A100)..."
python gpu_worker_rocketmq.py \
    --id "gpu-worker-2" \
    --gpu 0 \
    --gpu-model "A100" \
    --nameserver "$NAMESERVER" \
    --group-id "leetgpu_group" &
WORKER2_PID=$!
echo "Worker 2 PID: $WORKER2_PID"

# 启动Worker 3 (H100)
echo ""
echo "启动Worker 3 (H100)..."
python gpu_worker_rocketmq.py \
    --id "gpu-worker-3" \
    --gpu 0 \
    --gpu-model "H100" \
    --nameserver "$NAMESERVER" \
    --group-id "leetgpu_group" &
WORKER3_PID=$!
echo "Worker 3 PID: $WORKER3_PID"

echo ""
echo "========================================="
echo "所有服务已启动!"
echo "========================================="
echo "主节点: http://localhost:5000"
echo "按 Ctrl+C 停止所有服务"
echo "========================================="

# 等待中断信号
trap "kill $MASTER_PID $WORKER1_PID $WORKER2_PID $WORKER3_PID 2>/dev/null; exit" INT TERM

# 保持脚本运行
wait
