#!/usr/bin/env python3
"""
消息队列功能测试
"""

import time
import sys


def test_message_queue():
    """测试消息队列基本功能"""
    print("="*70)
    print("消息队列功能测试")
    print("="*70)
    print()
    
    from message_queue import get_message_queue
    
    # 创建消息队列
    print("1. 连接消息队列...")
    mq = get_message_queue()
    
    if mq.connected:
        print("   ✅ 已连接到Redis")
    else:
        print("   ⚠️  使用内存队列模式")
    
    # 健康检查
    print("\n2. 健康检查...")
    healthy = mq.health_check()
    print(f"   状态: {'✅ 健康' if healthy else '⚠️  降级'}")
    
    # 推送任务
    print("\n3. 推送测试任务...")
    task_data = {
        'task_id': 'test-001',
        'code': 'def test(): pass',
        'inputs': [],
        'grid_size': [1],
        'block_size': [1],
        'gpu_model': None
    }
    
    success = mq.push_task(task_data)
    print(f"   推送结果: {'✅ 成功' if success else '❌ 失败'}")
    
    # 查看队列大小
    print("\n4. 查询队列大小...")
    size = mq.get_queue_size()
    print(f"   队列大小: {size}")
    
    # 拉取任务
    print("\n5. 拉取任务...")
    pulled_task = mq.pull_task(timeout=2)
    if pulled_task:
        print(f"   ✅ 拉取成功: {pulled_task['task_id']}")
    else:
        print("   ⚠️  队列为空")
    
    # 保存结果
    print("\n6. 保存任务结果...")
    result = {
        'task_id': 'test-001',
        'status': 'completed',
        'result': [1, 2, 3],
        'worker_id': 'test-worker'
    }
    mq.set_task_result('test-001', result)
    print("   ✅ 结果已保存")
    
    # 获取结果
    print("\n7. 获取任务结果...")
    saved_result = mq.get_task_result('test-001')
    if saved_result:
        print(f"   ✅ 结果: {saved_result['status']}")
    else:
        print("   ⚠️  结果不存在")
    
    # Worker状态
    print("\n8. 更新Worker状态...")
    worker_status = {
        'worker_id': 'test-worker',
        'status': 'available',
        'gpu_utilization': 50.0,
        'memory_utilization': 60.0
    }
    mq.update_worker_status('test-worker', worker_status)
    print("   ✅ 状态已更新")
    
    # 获取Worker状态
    print("\n9. 获取Worker状态...")
    status = mq.get_worker_status('test-worker')
    if status:
        print(f"   ✅ 状态: {status['status']}")
    else:
        print("   ⚠️  状态不存在（可能已过期）")
    
    print("\n" + "="*70)
    print("测试完成")
    print("="*70)


def test_task_manager():
    """测试任务管理器"""
    print("\n" + "="*70)
    print("任务管理器测试（消息队列模式）")
    print("="*70)
    print()
    
    from task_manager_mq import TaskManagerMQ
    from config import GPU_WORKERS, REDIS_HOST, REDIS_PORT, REDIS_DB
    
    # 创建任务管理器
    print("1. 初始化任务管理器...")
    manager = TaskManagerMQ(GPU_WORKERS, REDIS_HOST, REDIS_PORT, REDIS_DB)
    
    # 启动监控
    print("\n2. 启动监控线程...")
    manager.start_monitor()
    print("   ✅ 监控已启动")
    
    # 健康检查
    print("\n3. 健康检查...")
    health = manager.health_check()
    print(f"   消息队列: {'✅' if health['message_queue'] else '❌'}")
    print(f"   队列大小: {health['queue_size']}")
    print(f"   总任务数: {health['total_tasks']}")
    print(f"   在线Worker: {health['workers_online']}")
    
    # Worker状态
    print("\n4. Worker状态...")
    workers = manager.get_worker_status()
    for w in workers:
        status_icon = "✅" if w['online'] else "❌"
        print(f"   {status_icon} {w['name']}: {w['status']}")
    
    # 提交任务
    print("\n5. 提交测试任务...")
    code = """
def vector_add(a, b, c):
    idx = cuda.grid(1)
    if idx < c.size:
        c[idx] = a[idx] + b[idx]
"""
    
    task_id = manager.submit_task(
        code=code,
        inputs=[],
        grid_size=(32,),
        block_size=(32,)
    )
    
    print(f"   ✅ 任务已提交: {task_id}")
    print(f"   队列大小: {manager.get_queue_size()}")
    
    # 等待处理
    print("\n6. 等待任务处理（3秒）...")
    for i in range(3):
        time.sleep(1)
        status = manager.get_task_status(task_id)
        if status:
            print(f"   [{i+1}/3] 状态: {status['status']}")
    
    # 停止监控
    print("\n7. 停止监控...")
    manager.stop_monitor()
    print("   ✅ 监控已停止")
    
    print("\n" + "="*70)
    print("测试完成")
    print("="*70)


def test_worker():
    """测试Worker（需要手动启动）"""
    print("\n" + "="*70)
    print("Worker测试说明")
    print("="*70)
    print()
    print("Worker需要在单独的进程中运行")
    print()
    print("启动Worker:")
    print("  ./start_worker_mq.sh --id test-worker --gpu 0")
    print()
    print("或者:")
    print("  python3 gpu_worker_mq.py --id test-worker --gpu 0")
    print()
    print("Worker将自动:")
    print("  1. 从消息队列拉取任务")
    print("  2. 检查GPU资源")
    print("  3. 执行CUDA JIT编译")
    print("  4. 保存结果到队列")
    print("  5. 发送心跳")
    print()


def main():
    """主函数"""
    print("\n" + "="*70)
    print("LeetGPU 消息队列架构测试")
    print("="*70)
    print()
    
    # 选择测试
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type == 'queue':
            test_message_queue()
        elif test_type == 'manager':
            test_task_manager()
        elif test_type == 'worker':
            test_worker()
        else:
            print(f"未知测试类型: {test_type}")
            print("可用类型: queue, manager, worker")
    else:
        # 运行所有测试
        try:
            test_message_queue()
            test_task_manager()
            test_worker()
        except KeyboardInterrupt:
            print("\n\n测试中断")
        except Exception as e:
            print(f"\n\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("测试说明")
    print("="*70)
    print()
    print("运行单个测试:")
    print("  python3 test_message_queue.py queue    # 测试消息队列")
    print("  python3 test_message_queue.py manager  # 测试任务管理器")
    print("  python3 test_message_queue.py worker   # Worker说明")
    print()
    print("完整测试:")
    print("  1. 确保Redis运行: redis-server")
    print("  2. 启动Worker: ./start_all_mq.sh")
    print("  3. 运行测试: python3 test_message_queue.py manager")
    print()


if __name__ == "__main__":
    main()
