#!/usr/bin/env python3
"""
主从架构测试脚本 - 验证系统功能
"""

import requests
import time
import sys
from typing import Dict, List


MASTER_URL = "http://localhost:5000"
TIMEOUT = 3


class TestMasterSlaveArchitecture:
    """主从架构测试类"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_results = []
    
    def test(self, name: str, func):
        """运行单个测试"""
        print(f"\n测试: {name}")
        print("-" * 60)
        try:
            func()
            print("✅ 通过")
            self.passed += 1
            self.test_results.append((name, True, None))
        except AssertionError as e:
            print(f"❌ 失败: {str(e)}")
            self.failed += 1
            self.test_results.append((name, False, str(e)))
        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            self.failed += 1
            self.test_results.append((name, False, str(e)))
    
    def test_master_online(self):
        """测试主节点是否在线"""
        response = requests.get(f"{MASTER_URL}/api/stats", timeout=TIMEOUT)
        assert response.status_code == 200, "主节点未响应"
        data = response.json()
        print(f"主节点在线，题目总数: {data['total']}")
    
    def test_workers_config(self):
        """测试Worker节点配置"""
        response = requests.get(f"{MASTER_URL}/api/workers", timeout=TIMEOUT)
        assert response.status_code == 200, "无法获取Worker配置"
        data = response.json()
        assert data['total'] > 0, "没有配置Worker节点"
        print(f"配置的Worker节点数: {data['total']}")
        for worker in data['workers']:
            print(f"  - {worker['name']}: {worker['gpu_model']}")
    
    def test_gpu_resources(self):
        """测试GPU资源监控"""
        response = requests.get(f"{MASTER_URL}/api/gpu/resources", timeout=TIMEOUT)
        assert response.status_code == 200, "无法获取GPU资源"
        data = response.json()
        assert 'resources' in data, "响应中缺少resources字段"
        
        print(f"GPU资源监控:")
        for gpu in data['resources']:
            status = "在线" if gpu.get('online') else "离线"
            print(f"  - {gpu['worker_name']}: {gpu['gpu_model']} ({status})")
            if gpu.get('online'):
                print(f"    GPU利用率: {gpu.get('gpu_utilization', 0):.1f}%")
                print(f"    显存使用: {gpu.get('memory_utilization', 0):.1f}%")
    
    def test_cluster_stats(self):
        """测试集群统计"""
        response = requests.get(f"{MASTER_URL}/api/cluster/stats", timeout=TIMEOUT)
        assert response.status_code == 200, "无法获取集群统计"
        data = response.json()
        
        print(f"集群统计:")
        print(f"  总Worker数: {data['total_workers']}")
        print(f"  在线Worker: {data['online_workers']}")
        print(f"  可用Worker: {data['available_workers']}")
        print(f"  总任务数: {data['total_tasks']}")
    
    def test_submit_simple_task(self):
        """测试提交简单任务"""
        code = """
def simple_kernel(output):
    idx = cuda.grid(1)
    if idx < output.size:
        output[idx] = idx * 2
"""
        
        task_data = {
            'code': code,
            'inputs': [
                {'data': [0] * 10, 'shape': [10], 'dtype': 'int32'}
            ],
            'grid_size': [1],
            'block_size': [10]
        }
        
        response = requests.post(f"{MASTER_URL}/api/submit-task", 
                                json=task_data, timeout=TIMEOUT)
        assert response.status_code == 200, "任务提交失败"
        data = response.json()
        assert 'task_id' in data, "响应中缺少task_id"
        
        task_id = data['task_id']
        print(f"任务已提交: {task_id}")
        print(f"状态: {data['status']}")
        
        # 等待任务完成或超时
        max_wait = 10
        for i in range(max_wait):
            time.sleep(1)
            status_response = requests.get(f"{MASTER_URL}/api/task/{task_id}", 
                                          timeout=TIMEOUT)
            status = status_response.json()
            print(f"  [{i+1}/{max_wait}] 状态: {status['status']}")
            
            if status['status'] in ['completed', 'failed', 'timeout']:
                break
        
        print(f"最终状态: {status['status']}")
        if status['status'] == 'completed':
            print("✅ 任务成功完成")
        elif status['status'] == 'failed':
            print(f"⚠️  任务失败: {status.get('error', 'Unknown')}")
        else:
            print(f"⚠️  任务超时或其他状态")
    
    def test_task_with_gpu_selection(self):
        """测试指定GPU型号提交任务"""
        code = """
def vector_add(a, b, c):
    idx = cuda.grid(1)
    if idx < c.size:
        c[idx] = a[idx] + b[idx]
"""
        
        task_data = {
            'code': code,
            'inputs': [],
            'grid_size': [1],
            'block_size': [1],
            'gpu_model': 'RTX 4090'  # 指定GPU型号
        }
        
        response = requests.post(f"{MASTER_URL}/api/submit-task", 
                                json=task_data, timeout=TIMEOUT)
        assert response.status_code == 200, "任务提交失败"
        data = response.json()
        
        print(f"指定GPU型号(RTX 4090)提交任务: {data['task_id']}")
        print(f"状态: {data['status']}")
    
    def test_api_endpoints(self):
        """测试所有API端点"""
        endpoints = [
            ('GET', '/api/challenges', 200),
            ('GET', '/api/stats', 200),
            ('GET', '/api/gpu-models', 200),
            ('GET', '/api/workers', 200),
            ('GET', '/api/gpu/resources', 200),
            ('GET', '/api/cluster/stats', 200),
            ('GET', '/api/tasks', 200),
        ]
        
        print("测试API端点:")
        for method, endpoint, expected_status in endpoints:
            try:
                if method == 'GET':
                    response = requests.get(f"{MASTER_URL}{endpoint}", timeout=TIMEOUT)
                status = response.status_code
                status_mark = "✅" if status == expected_status else "❌"
                print(f"  {status_mark} {method} {endpoint}: {status}")
                assert status == expected_status, f"期望状态码 {expected_status}，实际 {status}"
            except Exception as e:
                print(f"  ❌ {method} {endpoint}: {str(e)}")
                raise
    
    def test_web_pages(self):
        """测试Web页面"""
        pages = [
            ('/', '主页'),
            ('/quiz', '测验页面'),
        ]
        
        print("测试Web页面:")
        for url, name in pages:
            response = requests.get(f"{MASTER_URL}{url}", timeout=TIMEOUT)
            assert response.status_code == 200, f"{name}无法访问"
            assert len(response.text) > 0, f"{name}内容为空"
            print(f"  ✅ {name}: OK")
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("测试摘要")
        print("="*60)
        
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"总测试数: {total}")
        print(f"通过: {self.passed}")
        print(f"失败: {self.failed}")
        print(f"通过率: {pass_rate:.1f}%")
        
        if self.failed > 0:
            print("\n失败的测试:")
            for name, passed, error in self.test_results:
                if not passed:
                    print(f"  ❌ {name}")
                    if error:
                        print(f"     {error}")
        
        print("="*60)
        
        return self.failed == 0


def main():
    """主函数"""
    print("="*60)
    print("LeetGPU 主从架构测试")
    print("="*60)
    
    # 检查主节点是否在线
    print("\n检查主节点连接...")
    try:
        response = requests.get(f"{MASTER_URL}/api/stats", timeout=TIMEOUT)
        if response.status_code != 200:
            print("❌ 主节点未响应")
            print("\n请先启动主节点:")
            print("  cd website")
            print("  ./start_master.sh")
            sys.exit(1)
        print("✅ 主节点在线")
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到主节点: {e}")
        print("\n请先启动主节点:")
        print("  cd website")
        print("  ./start_master.sh")
        sys.exit(1)
    
    # 运行测试
    tester = TestMasterSlaveArchitecture()
    
    tester.test("主节点在线", tester.test_master_online)
    tester.test("Worker节点配置", tester.test_workers_config)
    tester.test("GPU资源监控", tester.test_gpu_resources)
    tester.test("集群统计", tester.test_cluster_stats)
    tester.test("API端点", tester.test_api_endpoints)
    tester.test("Web页面", tester.test_web_pages)
    tester.test("提交简单任务", tester.test_submit_simple_task)
    tester.test("指定GPU提交任务", tester.test_task_with_gpu_selection)
    
    # 打印摘要
    success = tester.print_summary()
    
    if success:
        print("\n🎉 所有测试通过！系统运行正常。")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败，请检查系统配置。")
        sys.exit(1)


if __name__ == "__main__":
    main()
