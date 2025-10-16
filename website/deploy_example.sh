#!/bin/bash
# 分布式部署示例脚本

echo "======================================"
echo "LeetGPU 分布式部署示例"
echo "======================================"
echo ""
echo "假设部署架构:"
echo "  主节点: 192.168.1.100 (CPU)"
echo "  GPU机器1: 192.168.1.101 (RTX 4090)"
echo "  GPU机器2: 192.168.1.102 (A100)"
echo "  GPU机器3: 192.168.1.103 (H100)"
echo ""
echo "======================================"
echo ""

read -p "请选择操作 (1=主节点部署, 2=GPU Worker部署, 3=验证): " choice

case $choice in
    1)
        echo "=== 主节点部署步骤 ==="
        echo ""
        echo "1. 配置Redis允许远程连接:"
        echo "   sudo sed -i 's/bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf"
        echo "   sudo systemctl restart redis"
        echo ""
        echo "2. 开放防火墙端口:"
        echo "   sudo ufw allow 6379/tcp"
        echo "   sudo ufw allow 5000/tcp"
        echo ""
        echo "3. 修改config.py中的GPU_WORKERS配置:"
        echo "   将host改为实际的GPU机器IP"
        echo ""
        echo "4. 启动主节点服务:"
        echo "   python3 app.py"
        echo ""
        ;;
    
    2)
        echo "=== GPU Worker部署步骤 ==="
        echo ""
        read -p "请输入主节点IP地址 (例: 192.168.1.100): " master_ip
        read -p "请输入Worker ID (例: gpu-worker-1): " worker_id
        read -p "请输入GPU设备ID (默认: 0): " gpu_id
        gpu_id=${gpu_id:-0}
        
        echo ""
        echo "部署配置:"
        echo "  主节点IP: $master_ip"
        echo "  Worker ID: $worker_id"
        echo "  GPU设备: $gpu_id"
        echo ""
        
        read -p "确认启动? (y/n): " confirm
        if [ "$confirm" = "y" ]; then
            echo ""
            echo "启动Worker..."
            python3 gpu_worker_mq.py \
                --id "$worker_id" \
                --gpu "$gpu_id" \
                --redis-host "$master_ip" \
                --redis-port 6379
        else
            echo "已取消"
        fi
        ;;
    
    3)
        echo "=== 部署验证步骤 ==="
        echo ""
        read -p "请输入主节点IP地址: " master_ip
        
        echo ""
        echo "1. 测试Redis连接..."
        if command -v redis-cli &> /dev/null; then
            redis-cli -h "$master_ip" -p 6379 ping
            if [ $? -eq 0 ]; then
                echo "   ✅ Redis连接成功"
            else
                echo "   ❌ Redis连接失败"
            fi
        else
            echo "   ⚠️  未安装redis-cli"
        fi
        
        echo ""
        echo "2. 测试网络连通性..."
        ping -c 3 "$master_ip"
        
        echo ""
        echo "3. 查看Worker状态..."
        if command -v redis-cli &> /dev/null; then
            echo "   在线Worker:"
            redis-cli -h "$master_ip" KEYS 'leetgpu:workers:status:*'
            
            echo ""
            echo "   队列大小:"
            redis-cli -h "$master_ip" LLEN leetgpu:tasks:queue
        fi
        ;;
    
    *)
        echo "无效选项"
        exit 1
        ;;
esac

echo ""
echo "======================================"
echo "详细部署文档: DISTRIBUTED_DEPLOYMENT.md"
echo "======================================"
