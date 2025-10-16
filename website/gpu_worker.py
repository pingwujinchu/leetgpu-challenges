"""
GPU Worker从节点服务 - 接收并执行GPU任务
"""

from flask import Flask, request, jsonify
import argparse
import sys
import os
from typing import Dict, Any
from datetime import datetime
import numpy as np
import json

# 导入自定义模块
from cuda_jit_wrapper import CudaJITWrapper
from gpu_monitor import GPUMonitor


class GPUWorker:
    """GPU Worker节点"""
    
    def __init__(self, worker_id: str, gpu_device_id: int = 0):
        """
        初始化GPU Worker
        
        Args:
            worker_id: Worker唯一标识
            gpu_device_id: GPU设备ID
        """
        self.worker_id = worker_id
        self.gpu_device_id = gpu_device_id
        self.cuda_wrapper = CudaJITWrapper()
        self.gpu_monitor = GPUMonitor(simulation_mode=True)  # 默认使用模拟模式
        
        # 任务结果缓存
        self.task_results = {}
        
        # 启动GPU监控
        self.gpu_monitor.start_monitoring(interval=2.0)
        
        print(f"GPU Worker {worker_id} 已初始化")
        print(f"使用GPU设备: {gpu_device_id}")
    
    def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行GPU任务
        
        Args:
            task_data: 任务数据字典
            
        Returns:
            执行结果字典
        """
        task_id = task_data.get('task_id')
        code = task_data.get('code')
        inputs_data = task_data.get('inputs', [])
        grid_size = tuple(task_data.get('grid_size', (1,)))
        block_size = tuple(task_data.get('block_size', (1,)))
        
        result = {
            'task_id': task_id,
            'worker_id': self.worker_id,
            'status': 'running',
            'started_at': datetime.now().isoformat()
        }
        
        try:
            # 验证代码
            is_valid, msg = self.cuda_wrapper.validate_cuda_code(code)
            if not is_valid:
                result['status'] = 'failed'
                result['error'] = f"代码验证失败: {msg}"
                self.task_results[task_id] = result
                return result
            
            # 编译内核
            try:
                kernel = self.cuda_wrapper.wrap_kernel(code)
            except Exception as e:
                result['status'] = 'failed'
                result['error'] = f"内核编译失败: {str(e)}"
                self.task_results[task_id] = result
                return result
            
            # 准备输入数据
            inputs = []
            for inp in inputs_data:
                if isinstance(inp, dict) and 'data' in inp:
                    # 从字典中恢复numpy数组
                    arr = np.array(inp['data'], dtype=inp.get('dtype', 'float32'))
                    if 'shape' in inp:
                        arr = arr.reshape(inp['shape'])
                    inputs.append(arr)
                else:
                    inputs.append(inp)
            
            # 执行内核
            if inputs:
                try:
                    outputs = self.cuda_wrapper.execute_kernel(
                        kernel, inputs, grid_size, block_size
                    )
                    
                    # 将numpy数组转换为可序列化的格式
                    serializable_outputs = []
                    for out in outputs:
                        if isinstance(out, np.ndarray):
                            serializable_outputs.append({
                                'data': out.tolist(),
                                'shape': out.shape,
                                'dtype': str(out.dtype)
                            })
                        else:
                            serializable_outputs.append(out)
                    
                    result['status'] = 'completed'
                    result['result'] = serializable_outputs
                    result['completed_at'] = datetime.now().isoformat()
                    
                except Exception as e:
                    result['status'] = 'failed'
                    result['error'] = f"内核执行失败: {str(e)}"
            else:
                result['status'] = 'completed'
                result['result'] = {'message': '任务已提交，但没有输入数据'}
                result['completed_at'] = datetime.now().isoformat()
            
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = f"执行任务时发生错误: {str(e)}"
        
        # 缓存结果
        self.task_results[task_id] = result
        return result
    
    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务结果字典
        """
        return self.task_results.get(task_id, {
            'task_id': task_id,
            'status': 'not_found',
            'error': '任务不存在'
        })
    
    def get_gpu_status(self) -> Dict[str, Any]:
        """获取GPU状态"""
        stats = self.gpu_monitor.get_latest_stats()
        
        # 返回当前设备的信息
        if stats and 'gpus' in stats and len(stats['gpus']) > self.gpu_device_id:
            gpu_info = stats['gpus'][self.gpu_device_id]
            return {
                'worker_id': self.worker_id,
                'gpu_device_id': self.gpu_device_id,
                'timestamp': stats['timestamp'],
                **gpu_info
            }
        
        return {
            'worker_id': self.worker_id,
            'gpu_device_id': self.gpu_device_id,
            'error': '无法获取GPU状态'
        }


# 创建Flask应用
def create_worker_app(worker_id: str, gpu_device_id: int = 0):
    """创建Worker Flask应用"""
    app = Flask(__name__)
    worker = GPUWorker(worker_id, gpu_device_id)
    
    @app.route('/health')
    def health_check():
        """健康检查"""
        return jsonify({
            'status': 'healthy',
            'worker_id': worker.worker_id,
            'gpu_device_id': worker.gpu_device_id
        })
    
    @app.route('/execute', methods=['POST'])
    def execute_task():
        """执行任务"""
        task_data = request.json
        
        if not task_data:
            return jsonify({'error': '缺少任务数据'}), 400
        
        # 异步执行任务（在实际生产环境中应该使用真正的异步处理）
        result = worker.execute_task(task_data)
        
        return jsonify(result)
    
    @app.route('/result/<task_id>')
    def get_result(task_id):
        """获取任务结果"""
        result = worker.get_task_result(task_id)
        return jsonify(result)
    
    @app.route('/gpu/status')
    def gpu_status():
        """获取GPU状态"""
        status = worker.get_gpu_status()
        return jsonify(status)
    
    @app.route('/gpu/info')
    def gpu_info():
        """获取GPU基本信息"""
        info = worker.gpu_monitor.get_gpu_info(worker.gpu_device_id)
        return jsonify({
            'worker_id': worker.worker_id,
            **info
        })
    
    return app


if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='GPU Worker节点')
    parser.add_argument('--id', type=str, required=True, help='Worker ID')
    parser.add_argument('--port', type=int, required=True, help='监听端口')
    parser.add_argument('--gpu', type=int, default=0, help='GPU设备ID')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址')
    
    args = parser.parse_args()
    
    # 创建并运行应用
    app = create_worker_app(args.id, args.gpu)
    
    print("\n" + "="*60)
    print(f"🚀 GPU Worker节点启动")
    print("="*60)
    print(f"Worker ID: {args.id}")
    print(f"GPU设备: {args.gpu}")
    print(f"监听地址: http://{args.host}:{args.port}")
    print("="*60 + "\n")
    
    app.run(host=args.host, port=args.port, debug=False)
