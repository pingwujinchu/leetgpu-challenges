"""
示例：如何提交任务到GPU Worker节点
"""

import requests
import json
import time
import numpy as np


# 主节点地址
MASTER_URL = "http://localhost:5000"


def submit_vector_add_task():
    """提交向量加法任务示例"""
    
    # 用户代码（CUDA JIT格式）
    cuda_code = """
def vector_add(a, b, c):
    '''向量加法核函数'''
    idx = cuda.grid(1)
    if idx < c.size:
        c[idx] = a[idx] + b[idx]
"""
    
    # 准备输入数据
    n = 1000
    a = np.arange(n, dtype=np.float32)
    b = np.arange(n, dtype=np.float32)
    c = np.zeros(n, dtype=np.float32)
    
    # 将numpy数组转换为可序列化格式
    inputs = [
        {'data': a.tolist(), 'shape': a.shape, 'dtype': str(a.dtype)},
        {'data': b.tolist(), 'shape': b.shape, 'dtype': str(b.dtype)},
        {'data': c.tolist(), 'shape': c.shape, 'dtype': str(c.dtype)}
    ]
    
    # 提交任务
    task_data = {
        'code': cuda_code,
        'inputs': inputs,
        'grid_size': [32],
        'block_size': [32],
        'gpu_model': 'RTX 4090'  # 指定GPU型号（可选）
    }
    
    print("提交任务到GPU Worker...")
    response = requests.post(f"{MASTER_URL}/api/submit-task", json=task_data)
    result = response.json()
    
    task_id = result['task_id']
    print(f"任务已提交: {task_id}")
    print(f"状态: {result['status']}")
    
    # 轮询任务状态
    print("\n等待任务完成...")
    while True:
        time.sleep(2)
        
        status_response = requests.get(f"{MASTER_URL}/api/task/{task_id}")
        status = status_response.json()
        
        print(f"任务状态: {status['status']}")
        
        if status['status'] == 'completed':
            print("\n任务完成！")
            print(f"Worker: {status['worker_id']}")
            print(f"执行时间: {status['started_at']} -> {status['completed_at']}")
            
            # 显示部分结果
            if status['result']:
                output = np.array(status['result'][2]['data'][:10])
                print(f"结果（前10个）: {output}")
            
            break
            
        elif status['status'] == 'failed':
            print(f"\n任务失败: {status.get('error', 'Unknown error')}")
            break
        
        elif status['status'] == 'timeout':
            print("\n任务超时")
            break


def get_gpu_resources():
    """获取GPU资源使用情况"""
    print("\n" + "="*60)
    print("GPU资源监控")
    print("="*60)
    
    response = requests.get(f"{MASTER_URL}/api/gpu/resources")
    data = response.json()
    
    print(f"总Worker节点数: {data['total_workers']}")
    print()
    
    for gpu in data['resources']:
        print(f"Worker: {gpu['worker_name']}")
        print(f"  GPU型号: {gpu['gpu_model']}")
        print(f"  显存: {gpu['gpu_memory_total']}")
        print(f"  计算能力: {gpu['compute_capability']}")
        print(f"  状态: {gpu['status']} ({'在线' if gpu['online'] else '离线'})")
        
        if gpu['online']:
            print(f"  GPU利用率: {gpu['gpu_utilization']:.1f}%")
            print(f"  显存使用: {gpu['memory_utilization']:.1f}%")
            print(f"  温度: {gpu['temperature']}°C")
            print(f"  功耗: {gpu['power_usage']:.1f}W")
        
        print()


def get_cluster_stats():
    """获取集群统计信息"""
    print("\n" + "="*60)
    print("集群统计")
    print("="*60)
    
    response = requests.get(f"{MASTER_URL}/api/cluster/stats")
    stats = response.json()
    
    print(f"总Worker数: {stats['total_workers']}")
    print(f"在线Worker: {stats['online_workers']}")
    print(f"忙碌Worker: {stats['busy_workers']}")
    print(f"可用Worker: {stats['available_workers']}")
    print(f"\n总任务数: {stats['total_tasks']}")
    print(f"任务统计:")
    for status, count in stats['task_stats'].items():
        print(f"  {status}: {count}")
    print(f"\nGPU型号: {', '.join(stats['gpu_models'])}")


def submit_matrix_multiply_task():
    """提交矩阵乘法任务示例"""
    
    cuda_code = """
def matrix_multiply(A, B, C):
    '''矩阵乘法核函数'''
    row = cuda.blockIdx.y * cuda.blockDim.y + cuda.threadIdx.y
    col = cuda.blockIdx.x * cuda.blockDim.x + cuda.threadIdx.x
    
    if row < C.shape[0] and col < C.shape[1]:
        sum_val = 0.0
        for k in range(A.shape[1]):
            sum_val += A[row, k] * B[k, col]
        C[row, col] = sum_val
"""
    
    # 准备输入数据
    m, n, k = 64, 64, 64
    A = np.random.rand(m, k).astype(np.float32)
    B = np.random.rand(k, n).astype(np.float32)
    C = np.zeros((m, n), dtype=np.float32)
    
    inputs = [
        {'data': A.tolist(), 'shape': A.shape, 'dtype': str(A.dtype)},
        {'data': B.tolist(), 'shape': B.shape, 'dtype': str(B.dtype)},
        {'data': C.tolist(), 'shape': C.shape, 'dtype': str(C.dtype)}
    ]
    
    task_data = {
        'code': cuda_code,
        'inputs': inputs,
        'grid_size': [2, 2],
        'block_size': [32, 32],
        'gpu_model': 'A100'  # 指定使用A100
    }
    
    print("\n提交矩阵乘法任务...")
    response = requests.post(f"{MASTER_URL}/api/submit-task", json=task_data)
    result = response.json()
    
    print(f"任务已提交: {result['task_id']}")
    print(f"状态: {result['status']}")
    
    return result['task_id']


if __name__ == "__main__":
    print("LeetGPU 主从架构 - 任务提交示例")
    print("="*60)
    
    # 检查主节点是否在线
    try:
        response = requests.get(f"{MASTER_URL}/api/stats", timeout=3)
        if response.status_code != 200:
            print("错误: 无法连接到主节点")
            print("请确保主节点已启动: ./start_master.sh")
            exit(1)
    except:
        print("错误: 无法连接到主节点")
        print("请确保主节点已启动: ./start_master.sh")
        exit(1)
    
    # 显示菜单
    while True:
        print("\n" + "="*60)
        print("请选择操作:")
        print("1. 查看GPU资源状态")
        print("2. 查看集群统计")
        print("3. 提交向量加法任务")
        print("4. 提交矩阵乘法任务")
        print("5. 退出")
        print("="*60)
        
        choice = input("请输入选项 (1-5): ").strip()
        
        if choice == '1':
            get_gpu_resources()
        elif choice == '2':
            get_cluster_stats()
        elif choice == '3':
            submit_vector_add_task()
        elif choice == '4':
            task_id = submit_matrix_multiply_task()
            print(f"任务ID: {task_id}")
            print("可以使用选项2查看任务状态")
        elif choice == '5':
            print("\n再见！")
            break
        else:
            print("无效的选项，请重试")
