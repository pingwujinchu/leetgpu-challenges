#!/usr/bin/env python3
"""
GPU阈值功能演示
展示任务如何在GPU资源不足时排队
"""

import time
import requests
from datetime import datetime


def print_section(title):
    """打印分节标题"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def check_gpu_status():
    """检查GPU状态"""
    try:
        response = requests.get('http://localhost:5000/api/gpu/resources', timeout=3)
        if response.status_code == 200:
            data = response.json()
            return data['resources']
        return None
    except:
        return None


def print_gpu_status(resources):
    """打印GPU状态"""
    if not resources:
        print("⚠️  无法获取GPU状态")
        return
    
    for gpu in resources:
        print(f"\n📊 {gpu['worker_name']} ({gpu['gpu_model']})")
        
        if not gpu['online']:
            print("   状态: ❌ 离线")
            continue
        
        memory_util = gpu.get('memory_utilization', 0)
        gpu_util = gpu.get('gpu_utilization', 0)
        
        # 显存状态
        memory_bar = '█' * int(memory_util / 10) + '░' * (10 - int(memory_util / 10))
        memory_icon = "🔴" if memory_util >= 90 else "🟢"
        print(f"   显存使用: [{memory_bar}] {memory_util:.1f}% {memory_icon}")
        
        # GPU利用率
        gpu_bar = '█' * int(gpu_util / 10) + '░' * (10 - int(gpu_util / 10))
        gpu_icon = "🔴" if gpu_util >= 95 else "🟢"
        print(f"   GPU利用率: [{gpu_bar}] {gpu_util:.1f}% {gpu_icon}")
        
        # 判断是否可用
        if memory_util >= 90 or gpu_util >= 95:
            print(f"   状态: ⏸️  不接受新任务（排队中）")
        else:
            print(f"   状态: ✅ 可接受新任务")


def simulate_scenario_1():
    """场景1: Worker资源充足，任务正常分配"""
    print_section("场景1: Worker资源充足")
    
    print("📝 场景说明:")
    print("   所有Worker的显存和GPU利用率都在阈值以下")
    print("   新任务应该能够正常分配到可用Worker")
    print()
    
    # 检查GPU状态
    resources = check_gpu_status()
    print_gpu_status(resources)
    
    print("\n💡 预期行为:")
    print("   ✓ 任务管理器选择资源充足的Worker")
    print("   ✓ 任务立即分配执行")
    print("   ✓ 无需排队等待")
    

def simulate_scenario_2():
    """场景2: 单个Worker资源不足"""
    print_section("场景2: 单个Worker资源不足")
    
    print("📝 场景说明:")
    print("   假设 Worker 1 的显存使用达到 92%（超过90%阈值）")
    print("   其他Worker资源正常")
    print()
    
    print("🔍 资源检查过程:")
    print()
    print("   [任务管理器] 检查 Worker 1 (RTX 4090)...")
    print("   [任务管理器] 查询GPU状态: /gpu/status")
    print("   [任务管理器] 显存利用率: 92.0%")
    print("   [任务管理器] 阈值检查: 92.0% >= 90% ❌")
    print("   [任务管理器] Worker 1 显存利用率 92.0% 超过阈值 90%，任务排队")
    print("   [任务管理器] 跳过 Worker 1，继续查找...")
    print()
    print("   [任务管理器] 检查 Worker 2 (A100)...")
    print("   [任务管理器] 查询GPU状态: /gpu/status")
    print("   [任务管理器] 显存利用率: 55.0%")
    print("   [任务管理器] 阈值检查: 55.0% < 90% ✅")
    print("   [任务管理器] Worker 2 资源充足")
    print("   [任务管理器] 任务分配到 Worker 2")
    print()
    
    print("💡 结果:")
    print("   ✓ 自动跳过资源不足的Worker")
    print("   ✓ 任务分配到资源充足的Worker 2")
    print("   ✓ 无需人工干预")


def simulate_scenario_3():
    """场景3: 所有Worker资源不足"""
    print_section("场景3: 所有Worker资源不足")
    
    print("📝 场景说明:")
    print("   所有Worker的显存使用都超过90%")
    print("   新任务无法立即执行")
    print()
    
    print("🔍 资源检查过程:")
    print()
    print("   [任务管理器] 检查 Worker 1 (RTX 4090)...")
    print("   [任务管理器] 显存利用率: 95.0% ❌ 超过阈值")
    print("   [任务管理器] 跳过 Worker 1")
    print()
    print("   [任务管理器] 检查 Worker 2 (A100)...")
    print("   [任务管理器] 显存利用率: 93.0% ❌ 超过阈值")
    print("   [任务管理器] 跳过 Worker 2")
    print()
    print("   [任务管理器] 检查 Worker 3 (H100)...")
    print("   [任务管理器] 显存利用率: 91.0% ❌ 超过阈值")
    print("   [任务管理器] 跳过 Worker 3")
    print()
    print("   [任务管理器] 所有Worker资源不足")
    print("   [任务管理器] 任务 task-123 保持在队列中")
    print("   [任务管理器] 状态: QUEUED")
    print()
    
    print("⏱️  等待过程:")
    for i in range(1, 6):
        print(f"   [{datetime.now().strftime('%H:%M:%S')}] 等待中... ({i*10}秒)")
        time.sleep(0.5)
    
    print()
    print("   [Worker 2] 任务完成，释放GPU资源")
    print("   [GPU监控] Worker 2 显存降至 65.0%")
    print()
    print("   [任务管理器] 检测到 Worker 2 资源可用")
    print("   [任务管理器] 自动分配任务 task-123 到 Worker 2")
    print("   [任务管理器] 任务开始执行")
    print("   [任务管理器] 状态: RUNNING")
    print()
    
    print("💡 结果:")
    print("   ✓ 任务自动排队等待")
    print("   ✓ 资源释放后自动分配")
    print("   ✓ 零人工干预")


def simulate_scenario_4():
    """场景4: 指定GPU型号且资源不足"""
    print_section("场景4: 指定GPU型号且资源不足")
    
    print("📝 场景说明:")
    print("   用户指定使用 RTX 4090")
    print("   但 RTX 4090 的显存使用达到 92%")
    print("   其他型号GPU（A100、H100）资源充足")
    print()
    
    print("🔍 资源检查过程:")
    print()
    print("   [用户] 提交任务，指定gpu_model='RTX 4090'")
    print("   [任务管理器] 查找 RTX 4090 类型的Worker...")
    print("   [任务管理器] 找到 Worker 1 (RTX 4090)")
    print("   [任务管理器] 检查 Worker 1 资源...")
    print("   [任务管理器] 显存利用率: 92.0% ❌ 超过阈值")
    print("   [任务管理器] Worker 1 资源不足")
    print("   [任务管理器] 不检查其他型号的Worker（用户指定RTX 4090）")
    print("   [任务管理器] 任务保持在队列中")
    print("   [任务管理器] 等待 RTX 4090 资源释放")
    print()
    
    print("💡 行为说明:")
    print("   ✓ 尊重用户的GPU型号选择")
    print("   ✓ 不会分配到其他型号的GPU")
    print("   ✓ 等待指定型号的资源释放")
    print()
    print("💡 建议:")
    print("   - 如果不指定GPU型号，系统会自动选择任意可用Worker")
    print("   - 指定GPU型号适合需要特定计算能力的任务")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("  🎯 GPU资源阈值功能演示")
    print("="*70)
    print()
    print("本演示将展示以下场景：")
    print("  1️⃣  Worker资源充足 → 任务正常分配")
    print("  2️⃣  单个Worker资源不足 → 跳过该Worker")
    print("  3️⃣  所有Worker资源不足 → 任务排队")
    print("  4️⃣  指定GPU型号且资源不足 → 等待指定GPU")
    print()
    
    # 检查主节点连接
    print("🔍 检查主节点连接...")
    try:
        response = requests.get('http://localhost:5000/api/stats', timeout=3)
        if response.status_code == 200:
            print("✅ 主节点在线\n")
            
            # 显示当前GPU状态
            print_section("当前GPU资源状态")
            resources = check_gpu_status()
            print_gpu_status(resources)
            
        else:
            print("❌ 主节点未响应")
            print("\n请先启动主节点: ./start_all.sh")
            return
            
    except:
        print("❌ 无法连接到主节点")
        print("\n请先启动主节点:")
        print("  cd website")
        print("  ./start_all.sh")
        print("\n然后重新运行演示:")
        print("  python3 demo_gpu_threshold.py")
        return
    
    # 演示各个场景
    input("\n按Enter继续查看场景演示...")
    
    simulate_scenario_1()
    input("\n按Enter继续...")
    
    simulate_scenario_2()
    input("\n按Enter继续...")
    
    simulate_scenario_3()
    input("\n按Enter继续...")
    
    simulate_scenario_4()
    
    # 总结
    print_section("功能总结")
    print("✨ GPU资源阈值功能特点：")
    print()
    print("   1. 🔍 实时检测: 任务分配前实时查询GPU状态")
    print("   2. 🚦 自动过滤: 资源不足的Worker自动跳过")
    print("   3. ⏸️  智能排队: 所有Worker不可用时自动排队")
    print("   4. 🔄 自动恢复: 资源释放后任务自动分配")
    print("   5. ⚙️  灵活配置: 可调整阈值适应不同场景")
    print("   6. 🎯 型号选择: 支持指定GPU型号的任务")
    print()
    print("📊 默认阈值:")
    print("   • 显存利用率: 90%")
    print("   • GPU利用率: 95%")
    print()
    print("📝 配置文件: config.py")
    print("   GPU_MEMORY_THRESHOLD = 90")
    print("   GPU_UTILIZATION_THRESHOLD = 95")
    print()
    
    print("="*70)
    print()
    print("🎉 演示完成！")
    print()
    print("下一步:")
    print("  • 查看详细文档: GPU_THRESHOLD_FEATURE.md")
    print("  • 运行实际测试: python3 test_gpu_threshold.py")
    print("  • 访问Web界面: http://localhost:5000")
    print("  • 提交测试任务: python3 example_task_submission.py")
    print()


if __name__ == "__main__":
    main()
