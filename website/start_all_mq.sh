#!/bin/bash
# 启动所有节点（消息队列模式）

echo "======================================"
echo "启动 LeetGPU 主从架构集群"
echo "（消息队列模式）"
echo "======================================"

# 检查Redis是否运行
echo "检查Redis服务..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis服务正在运行"
    else
        echo "⚠️  Redis服务未运行"
        echo "请启动Redis服务:"
        echo "  - Linux/Mac: redis-server"
        echo "  - Docker: docker run -d -p 6379:6379 redis:alpine"
        echo ""
        echo "或者系统将使用内存队列模式（无持久化）"
        sleep 2
    fi
else
    echo "⚠️  未找到redis-cli命令"
    echo "系统将使用内存队列模式（无持久化）"
    sleep 2
fi

echo ""

# 创建日志目录
mkdir -p logs

# 启动Worker节点（后台运行）
echo "启动 Worker 1 (RTX 4090)..."
./start_worker_mq.sh --id gpu-worker-1 --gpu 0 > logs/worker1_mq.log 2>&1 &
WORKER1_PID=$!
sleep 1

echo "启动 Worker 2 (A100)..."
./start_worker_mq.sh --id gpu-worker-2 --gpu 0 > logs/worker2_mq.log 2>&1 &
WORKER2_PID=$!
sleep 1

echo "启动 Worker 3 (H100)..."
./start_worker_mq.sh --id gpu-worker-3 --gpu 0 > logs/worker3_mq.log 2>&1 &
WORKER3_PID=$!
sleep 1

echo ""
echo "✅ Worker节点已启动（后台运行）"
echo "   查看日志: tail -f logs/worker*_mq.log"
echo ""
echo "启动主节点..."
echo "（使用 app_mq.py 或在 app.py 中选择消息队列模式）"
echo ""
echo "======================================"
echo "集群已启动"
echo "======================================"
echo ""
echo "提示:"
echo "  - 主节点将自动使用消息队列模式"
echo "  - Worker从消息队列拉取任务"
echo "  - 队列大小: redis-cli LLEN leetgpu:tasks:queue"
echo "  - Worker状态: redis-cli KEYS 'leetgpu:workers:status:*'"
echo ""
echo "按 Ctrl+C 停止所有Worker"
echo ""

# 清理函数
cleanup() {
    echo ""
    echo "正在关闭所有Worker节点..."
    kill $WORKER1_PID $WORKER2_PID $WORKER3_PID 2>/dev/null
    echo "所有Worker节点已关闭"
    exit 0
}

# 捕获退出信号
trap cleanup SIGINT SIGTERM

# 保持脚本运行
wait
