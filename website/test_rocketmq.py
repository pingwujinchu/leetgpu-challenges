"""
RocketMQ消息队列测试脚本
"""

import time
import sys
from message_queue_rocketmq import MessageQueueRocketMQ

def test_basic_operations():
    """测试基本操作"""
    print("\n" + "="*70)
    print("RocketMQ 消息队列基本功能测试")
    print("="*70)
    
    # 创建消息队列实例
    mq = MessageQueueRocketMQ(nameserver='localhost:9876', group_id='test_group')
    
    # 1. 健康检查
    print("\n[1] 健康检查...")
    is_healthy = mq.health_check()
    status = "✅ 正常" if is_healthy else "❌ 异常"
    print(f"    状态: {status}")
    print(f"    连接: {'已连接' if mq.connected else '未连接（内存模式）'}")
    
    if not mq.connected:
        print("\n⚠️  未连接到RocketMQ，使用内存模式进行测试")
    
    # 2. 推送任务
    print("\n[2] 推送任务...")
    task_data = {
        'task_id': 'test-task-001',
        'code': 'def vector_add(a, b, c): pass',
        'inputs': [],
        'grid_size': [32],
        'block_size': [32],
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    success = mq.push_task(task_data, gpu_model='RTX 4090')
    print(f"    推送结果: {'✅ 成功' if success else '❌ 失败'}")
    
    # 3. 保存任务结果
    print("\n[3] 保存任务结果...")
    result_data = {
        'task_id': 'test-task-001',
        'status': 'completed',
        'result': [1, 2, 3, 4, 5],
        'worker_id': 'test-worker-1',
        'completed_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    mq.set_task_result('test-task-001', result_data)
    print(f"    保存成功")
    
    # 等待结果传播
    time.sleep(1)
    
    # 4. 获取任务结果
    print("\n[4] 获取任务结果...")
    retrieved_result = mq.get_task_result('test-task-001')
    if retrieved_result:
        print(f"    ✅ 获取成功")
        print(f"    任务ID: {retrieved_result.get('task_id')}")
        print(f"    状态: {retrieved_result.get('status')}")
        print(f"    Worker: {retrieved_result.get('worker_id')}")
    else:
        print(f"    ❌ 未找到结果")
    
    # 5. 更新Worker状态
    print("\n[5] 更新Worker状态...")
    worker_status = {
        'worker_id': 'test-worker-1',
        'status': 'available',
        'gpu_utilization': 25.5,
        'memory_utilization': 30.2,
        'temperature': 45,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    mq.update_worker_status('test-worker-1', worker_status)
    print(f"    更新成功")
    
    # 等待状态传播
    time.sleep(1)
    
    # 6. 获取Worker状态
    print("\n[6] 获取Worker状态...")
    retrieved_status = mq.get_worker_status('test-worker-1')
    if retrieved_status:
        print(f"    ✅ 获取成功")
        print(f"    Worker ID: {retrieved_status.get('worker_id')}")
        print(f"    状态: {retrieved_status.get('status')}")
        print(f"    GPU利用率: {retrieved_status.get('gpu_utilization')}%")
    else:
        print(f"    ❌ 未找到状态")
    
    # 7. 获取所有Worker状态
    print("\n[7] 获取所有Worker状态...")
    all_status = mq.get_all_worker_status()
    print(f"    找到 {len(all_status)} 个Worker")
    for worker_id, status in all_status.items():
        print(f"    - {worker_id}: {status.get('status')}")
    
    # 8. 队列大小
    print("\n[8] 查询队列大小...")
    queue_size = mq.get_queue_size()
    print(f"    队列大小: {queue_size}")
    
    all_sizes = mq.get_all_queue_sizes()
    print(f"    所有队列: {all_sizes}")
    
    # 关闭连接
    print("\n[9] 关闭连接...")
    mq.shutdown()
    print(f"    ✅ 已关闭")
    
    print("\n" + "="*70)
    print("测试完成")
    print("="*70 + "\n")


def test_gpu_routing():
    """测试GPU型号路由功能"""
    print("\n" + "="*70)
    print("RocketMQ GPU型号路由测试")
    print("="*70)
    
    mq = MessageQueueRocketMQ(nameserver='localhost:9876', group_id='routing_test_group')
    
    print("\n推送不同GPU型号的任务...")
    
    # 推送到不同GPU型号队列
    gpu_models = ['RTX 4090', 'A100', 'H100', None]
    
    for i, gpu_model in enumerate(gpu_models):
        task_data = {
            'task_id': f'routing-test-{i+1}',
            'code': f'def test_{i+1}(): pass',
            'inputs': [],
            'grid_size': [32],
            'block_size': [32],
            'gpu_model': gpu_model
        }
        
        success = mq.push_task(task_data, gpu_model=gpu_model)
        model_name = gpu_model if gpu_model else '通用队列'
        status = "✅" if success else "❌"
        print(f"  {status} 任务 {i+1} -> {model_name}")
    
    print("\n队列状态:")
    all_sizes = mq.get_all_queue_sizes()
    for queue_name, size in all_sizes.items():
        print(f"  - {queue_name}: {size} 个任务")
    
    mq.shutdown()
    print("\n" + "="*70)
    print("路由测试完成")
    print("="*70 + "\n")


def test_performance():
    """性能测试"""
    print("\n" + "="*70)
    print("RocketMQ 性能测试")
    print("="*70)
    
    mq = MessageQueueRocketMQ(nameserver='localhost:9876', group_id='perf_test_group')
    
    if not mq.connected:
        print("\n⚠️  未连接到RocketMQ，跳过性能测试")
        return
    
    # 批量推送任务
    num_tasks = 100
    print(f"\n推送 {num_tasks} 个任务...")
    
    start_time = time.time()
    success_count = 0
    
    for i in range(num_tasks):
        task_data = {
            'task_id': f'perf-test-{i}',
            'code': f'def test_{i}(): pass',
            'inputs': [],
            'grid_size': [32],
            'block_size': [32]
        }
        
        if mq.push_task(task_data):
            success_count += 1
        
        if (i + 1) % 20 == 0:
            print(f"  已推送 {i+1}/{num_tasks} 个任务...")
    
    elapsed_time = time.time() - start_time
    
    print(f"\n推送完成:")
    print(f"  总数: {num_tasks}")
    print(f"  成功: {success_count}")
    print(f"  失败: {num_tasks - success_count}")
    print(f"  耗时: {elapsed_time:.2f} 秒")
    print(f"  吞吐量: {success_count / elapsed_time:.2f} 任务/秒")
    
    mq.shutdown()
    print("\n" + "="*70)
    print("性能测试完成")
    print("="*70 + "\n")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("RocketMQ 消息队列测试套件")
    print("="*70)
    print("\n请确保RocketMQ服务已启动:")
    print("  NameServer: localhost:9876")
    print("\n如果RocketMQ未启动，测试将使用内存模式运行")
    print("="*70)
    
    input("\n按 Enter 继续...")
    
    try:
        # 运行测试
        test_basic_operations()
        test_gpu_routing()
        
        # 性能测试（可选）
        choice = input("\n是否运行性能测试? (y/n): ")
        if choice.lower() == 'y':
            test_performance()
        
        print("\n✅ 所有测试完成!")
        
    except KeyboardInterrupt:
        print("\n\n测试被中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
