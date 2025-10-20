#!/bin/bash

# GPU Worker启动脚本 (RocketMQ版本)

WORKER_ID=${1:-"gpu-worker-1"}
GPU_DEVICE=${2:-0}
GPU_MODEL=${3:-"RTX 4090"}
NAMESERVER=${4:-"localhost:9876"}
GROUP_ID=${5:-"leetgpu_group"}

echo "========================================="
echo "启动GPU Worker (RocketMQ模式)"
echo "========================================="
echo "Worker ID: $WORKER_ID"
echo "GPU设备: $GPU_DEVICE"
echo "GPU型号: $GPU_MODEL"
echo "NameServer: $NAMESERVER"
echo "消费者组: $GROUP_ID"
echo "========================================="

python gpu_worker_rocketmq.py \
    --id "$WORKER_ID" \
    --gpu "$GPU_DEVICE" \
    --gpu-model "$GPU_MODEL" \
    --nameserver "$NAMESERVER" \
    --group-id "$GROUP_ID"
