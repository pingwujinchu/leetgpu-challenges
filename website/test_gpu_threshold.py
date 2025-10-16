#!/usr/bin/env python3
"""
测试GPU资源阈值功能
演示当GPU显存或利用率超过阈值时任务排队
"""

import time
import sys


def test_gpu_threshold():
    """测试GPU阈值功能"""
    
    print("="*60)
    print("GPU资源阈值测试")
    print("="*60)
    print()
    
    print("配置说明:")
    print("  - 显存利用率阈值: 90%")
    print("  - GPU利用率阈值: 95%")
    print("  - 当GPU资源超过阈值时，新任务将排队等待")
    print()
    
    # 检查配置
    try:
        from config import GPU_MEMORY_THRESHOLD, GPU_UTILIZATION_THRESHOLD
        print(f"✅ 当前配置:")
        print(f"   显存阈值: {GPU_MEMORY_THRESHOLD}%")
        print(f"   GPU利用率阈值: {GPU_UTILIZATION_THRESHOLD}%")
    except ImportError:
        print("⚠️  使用默认配置:")
        print("   显存阈值: 90%")
        print("   GPU利用率阈值: 95%")
    
    print()
    print("-"*60)
    print("工作原理:")
    print("-"*60)
    print()
    print("1. 任务管理器在选择Worker时会先检查GPU资源")
    print("2. 查询Worker的GPU状态（利用率、显存使用率）")
    print("3. 如果显存利用率 >= 90% 或 GPU利用率 >= 95%：")
    print("   - 跳过该Worker")
    print("   - 继续检查下一个Worker")
    print("   - 如果所有Worker都不可用，任务保持在队列中")
    print("4. 当GPU资源降低后，任务会自动分配执行")
    print()
    
    print("-"*60)
    print("示例场景:")
    print("-"*60)
    print()
    print("场景1: Worker 1 显存使用 92%")
    print("  → 检测到超过阈值90%")
    print("  → 跳过Worker 1")
    print("  → 检查Worker 2...")
    print()
    print("场景2: 所有Worker显存都超过90%")
    print("  → 所有Worker都不可用")
    print("  → 任务保持在队列中")
    print("  → 等待任何Worker资源释放")
    print()
    print("场景3: Worker 1 显存降到85%")
    print("  → 资源充足")
    print("  → 队列中的任务自动分配到Worker 1")
    print("  → 开始执行")
    print()
    
    print("-"*60)
    print("实时测试")
    print("-"*60)
    print()
    
    try:
        import requests
        
        # 检查主节点
        print("检查主节点连接...")
        response = requests.get('http://localhost:5000/api/gpu/resources', timeout=3)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 主节点在线\n")
            
            print("当前GPU资源状态:")
            print("-"*60)
            
            for gpu in data['resources']:
                print(f"\n{gpu['worker_name']} ({gpu['gpu_model']})")
                
                if gpu['online']:
                    memory_util = gpu.get('memory_utilization', 0)
                    gpu_util = gpu.get('gpu_utilization', 0)
                    
                    # 判断是否超过阈值
                    memory_status = "🔴 超过阈值" if memory_util >= 90 else "🟢 正常"
                    gpu_status = "🔴 超过阈值" if gpu_util >= 95 else "🟢 正常"
                    
                    print(f"  显存使用: {memory_util:.1f}% {memory_status}")
                    print(f"  GPU利用率: {gpu_util:.1f}% {gpu_status}")
                    
                    if memory_util >= 90 or gpu_util >= 95:
                        print(f"  状态: ⏸️  不接受新任务（排队中）")
                    else:
                        print(f"  状态: ✅ 可接受新任务")
                else:
                    print("  状态: ❌ 离线")
            
            print("\n" + "-"*60)
            print("\n💡 提示:")
            print("  - 可以通过修改 config.py 调整阈值")
            print("  - 访问 http://localhost:5000 查看实时GPU状态")
            print("  - 提交任务会自动选择资源充足的Worker")
            
        else:
            print("❌ 主节点未响应")
            print("\n请先启动主节点:")
            print("  ./start_all.sh")
            
    except requests.exceptions.RequestException:
        print("❌ 无法连接到主节点")
        print("\n请先启动主节点:")
        print("  cd website")
        print("  ./start_all.sh")
        print("\n然后重新运行此测试:")
        print("  python3 test_gpu_threshold.py")
    
    print("\n" + "="*60)
    print()


def simulate_high_memory():
    """模拟高显存使用场景"""
    print("\n" + "="*60)
    print("模拟高显存使用场景")
    print("="*60)
    print()
    print("注意: 这是一个演示说明，实际的GPU状态由gpu_monitor.py生成")
    print()
    print("模拟场景:")
    print("  1. Worker 1 显存从 60% 增加到 92%")
    print("  2. 系统检测到超过90%阈值")
    print("  3. 新任务不再分配到Worker 1")
    print("  4. 任务自动分配到其他可用Worker")
    print("  5. 如果所有Worker都满，任务排队")
    print()
    print("日志输出示例:")
    print("-"*60)
    print("[任务管理器] 检查Worker gpu-worker-1...")
    print("[任务管理器] Worker gpu-worker-1 显存利用率 92.0% 超过阈值 90%，任务排队")
    print("[任务管理器] Worker gpu-worker-1 (RTX 4090) 资源不足，继续查找...")
    print("[任务管理器] 检查Worker gpu-worker-2...")
    print("[任务管理器] Worker gpu-worker-2 资源充足")
    print("[任务管理器] 任务分配到Worker gpu-worker-2 (A100)")
    print("-"*60)
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--simulate":
        simulate_high_memory()
    else:
        test_gpu_threshold()
    
    print("测试完成！")
    print()
    print("下一步:")
    print("  1. 启动系统: ./start_all.sh")
    print("  2. 访问网站: http://localhost:5000")
    print("  3. 提交任务: python3 example_task_submission.py")
    print("  4. 观察GPU资源变化和任务分配情况")
    print()
