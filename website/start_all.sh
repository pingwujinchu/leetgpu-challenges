#!/bin/bash
# 启动所有节点（主节点 + 3个Worker节点）

echo "======================================"
echo "启动 LeetGPU 主从架构集群"
echo "======================================"

# 创建日志目录
mkdir -p logs

# 启动Worker节点（后台运行）
echo "启动 Worker 1 (RTX 4090)..."
./start_worker.sh --id gpu-worker-1 --port 5001 --gpu 0 > logs/worker1.log 2>&1 &
WORKER1_PID=$!

echo "启动 Worker 2 (A100)..."
./start_worker.sh --id gpu-worker-2 --port 5002 --gpu 0 > logs/worker2.log 2>&1 &
WORKER2_PID=$!

echo "启动 Worker 3 (H100)..."
./start_worker.sh --id gpu-worker-3 --port 5003 --gpu 0 > logs/worker3.log 2>&1 &
WORKER3_PID=$!

# 等待Worker节点启动
echo "等待Worker节点启动..."
sleep 3

# 启动主节点（前台运行）
echo ""
echo "启动主节点..."
echo ""
./start_master.sh

# 清理函数
cleanup() {
    echo ""
    echo "正在关闭所有节点..."
    kill $WORKER1_PID $WORKER2_PID $WORKER3_PID 2>/dev/null
    echo "所有节点已关闭"
    exit 0
}

# 捕获退出信号
trap cleanup SIGINT SIGTERM

# 保持脚本运行
wait
