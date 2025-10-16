#!/usr/bin/env python3
"""
GPU型号路由功能测试
演示不同GPU型号的Worker只拉取匹配的任务
"""

import time
import sys


def demo_gpu_routing():
    """演示GPU型号路由功能"""
    print("="*70)
    print("GPU型号路由功能演示")
    print("="*70)
    print()
    
    print("📋 场景说明:")
    print("  GPU机器1: 4张 RTX 4090")
    print("  GPU机器2: 8张 A100")
    print("  GPU机器3: 8张 H100")
    print()
    print("  每个Worker只拉取匹配其GPU型号的任务")
    print()
    
    print("-"*70)
    print("队列结构:")
    print("-"*70)
    print()
    print("  leetgpu:tasks:queue           ← 通用队列（任意GPU可拉取）")
    print("  leetgpu:tasks:queue:RTX 4090  ← RTX 4090专用队列")
    print("  leetgpu:tasks:queue:A100      ← A100专用队列")
    print("  leetgpu:tasks:queue:H100      ← H100专用队列")
    print()
    
    print("-"*70)
    print("任务路由示例:")
    print("-"*70)
    print()
    
    print("📤 任务1: 指定 gpu_model='RTX 4090'")
    print("   → 推送到: leetgpu:tasks:queue:RTX 4090")
    print("   → RTX 4090 Worker 拉取顺序:")
    print("      1. leetgpu:tasks:queue:RTX 4090 (优先)")
    print("      2. leetgpu:tasks:queue (其次)")
    print("   → A100 Worker 拉取顺序:")
    print("      1. leetgpu:tasks:queue:A100")
    print("      2. leetgpu:tasks:queue")
    print("   ✅ 结果: 只有RTX 4090 Worker会拉取此任务")
    print()
    
    print("📤 任务2: 指定 gpu_model='A100'")
    print("   → 推送到: leetgpu:tasks:queue:A100")
    print("   ✅ 结果: 只有A100 Worker会拉取此任务")
    print()
    
    print("📤 任务3: 未指定 gpu_model (None)")
    print("   → 推送到: leetgpu:tasks:queue (通用队列)")
    print("   ✅ 结果: 所有Worker都可以拉取（竞争）")
    print()
    
    print("-"*70)
    print("Worker拉取策略:")
    print("-"*70)
    print()
    
    print("🔧 RTX 4090 Worker (gpu_model='RTX 4090'):")
    print("   监听队列: ['leetgpu:tasks:queue:RTX 4090',")
    print("             'leetgpu:tasks:queue']")
    print("   优先级: RTX 4090队列 > 通用队列")
    print("   拉取: BLPOP命令自动按顺序拉取")
    print()
    
    print("🔧 A100 Worker (gpu_model='A100'):")
    print("   监听队列: ['leetgpu:tasks:queue:A100',")
    print("             'leetgpu:tasks:queue']")
    print("   只拉取: A100任务 + 通用任务")
    print()
    
    print("🔧 通用Worker (gpu_model=None):")
    print("   监听队列: ['leetgpu:tasks:queue']")
    print("   只拉取: 通用任务")
    print()


def test_message_queue():
    """测试消息队列的GPU路由功能"""
    print("\n" + "="*70)
    print("消息队列GPU路由测试")
    print("="*70)
    print()
    
    try:
        from message_queue import get_message_queue
        
        mq = get_message_queue()
        
        print(f"连接状态: {'✅ Redis' if mq.connected else '⚠️  内存模式'}")
        print()
        
        if not mq.connected:
            print("⚠️  需要Redis才能测试GPU路由功能")
            print("   请启动Redis: redis-server")
            return
        
        # 清空队列
        print("1. 清空所有队列...")
        mq.clear_queue()
        print("   ✅ 队列已清空")
        print()
        
        # 推送不同GPU型号的任务
        print("2. 推送不同GPU型号的任务...")
        
        tasks = [
            ({'task_id': 'task-rtx-1', 'code': '...'}, 'RTX 4090'),
            ({'task_id': 'task-rtx-2', 'code': '...'}, 'RTX 4090'),
            ({'task_id': 'task-a100-1', 'code': '...'}, 'A100'),
            ({'task_id': 'task-a100-2', 'code': '...'}, 'A100'),
            ({'task_id': 'task-h100-1', 'code': '...'}, 'H100'),
            ({'task_id': 'task-common-1', 'code': '...'}, None),
        ]
        
        for task_data, gpu_model in tasks:
            mq.push_task(task_data, gpu_model=gpu_model)
        
        print()
        
        # 查看队列大小
        print("3. 查看各队列大小...")
        sizes = mq.get_all_queue_sizes()
        for queue_name, size in sizes.items():
            print(f"   {queue_name}: {size} 任务")
        print()
        
        # 模拟RTX 4090 Worker拉取
        print("4. 模拟 RTX 4090 Worker 拉取...")
        task = mq.pull_task(gpu_models=['RTX 4090'], timeout=1)
        if task:
            print(f"   ✅ 拉取到: {task['task_id']}")
        else:
            print("   ⚠️  队列为空")
        print()
        
        # 模拟A100 Worker拉取
        print("5. 模拟 A100 Worker 拉取...")
        task = mq.pull_task(gpu_models=['A100'], timeout=1)
        if task:
            print(f"   ✅ 拉取到: {task['task_id']}")
        else:
            print("   ⚠️  队列为空")
        print()
        
        # 模拟H100 Worker拉取
        print("6. 模拟 H100 Worker 拉取...")
        task = mq.pull_task(gpu_models=['H100'], timeout=1)
        if task:
            print(f"   ✅ 拉取到: {task['task_id']}")
        else:
            print("   ⚠️  队列为空")
        print()
        
        # 模拟通用Worker拉取
        print("7. 模拟通用Worker拉取...")
        task = mq.pull_task(gpu_models=None, timeout=1)
        if task:
            print(f"   ✅ 拉取到: {task['task_id']}")
        else:
            print("   ⚠️  队列为空")
        print()
        
        # 最终队列状态
        print("8. 最终队列状态...")
        sizes = mq.get_all_queue_sizes()
        for queue_name, size in sizes.items():
            print(f"   {queue_name}: {size} 任务")
        
        print()
        print("✅ GPU路由功能测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def show_usage():
    """显示使用说明"""
    print("\n" + "="*70)
    print("GPU型号路由 - 使用说明")
    print("="*70)
    print()
    
    print("🎯 功能:")
    print("  每个Worker指定GPU型号，只拉取匹配的任务")
    print()
    
    print("🚀 启动Worker:")
    print()
    print("  # 指定GPU型号")
    print("  ./start_worker_mq.sh \\")
    print("      --id worker-1 \\")
    print("      --gpu 0 \\")
    print("      --gpu-model \"RTX 4090\" \\")
    print("      --redis-host 192.168.1.100")
    print()
    print("  # 自动检测（推荐）")
    print("  ./start_multi_gpu_workers.sh")
    print()
    
    print("📤 提交任务:")
    print()
    print("  from task_manager_mq import TaskManagerMQ")
    print()
    print("  # 提交到RTX 4090队列")
    print("  manager.submit_task(..., gpu_model='RTX 4090')")
    print()
    print("  # 提交到通用队列")
    print("  manager.submit_task(..., gpu_model=None)")
    print()
    
    print("🔍 监控队列:")
    print()
    print("  # 查看所有队列")
    print("  redis-cli KEYS 'leetgpu:tasks:queue*'")
    print()
    print("  # 查看队列大小")
    print("  redis-cli LLEN 'leetgpu:tasks:queue:RTX 4090'")
    print()
    
    print("📚 详细文档:")
    print("  GPU_MODEL_ROUTING.md")
    print()


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_message_queue()
    elif len(sys.argv) > 1 and sys.argv[1] == 'usage':
        show_usage()
    else:
        demo_gpu_routing()
        
        print("\n" + "="*70)
        print("运行测试:")
        print("  python3 test_gpu_routing.py test")
        print()
        print("查看使用说明:")
        print("  python3 test_gpu_routing.py usage")
        print("="*70)
        print()


if __name__ == "__main__":
    main()
