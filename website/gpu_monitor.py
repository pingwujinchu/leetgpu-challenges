"""
GPU资源监控模块 - 监控GPU使用情况
"""

import time
import threading
from typing import Dict, List, Optional
from datetime import datetime


try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False
    print("Warning: pynvml not available. GPU monitoring will use simulation mode.")


class GPUMonitor:
    """GPU资源监控器"""
    
    def __init__(self, simulation_mode: bool = False):
        """
        初始化GPU监控器
        
        Args:
            simulation_mode: 是否使用模拟模式（当无法访问真实GPU时）
        """
        self.simulation_mode = simulation_mode or not NVML_AVAILABLE
        self.monitoring = False
        self.monitor_thread = None
        self.gpu_stats = {}
        
        if not self.simulation_mode:
            try:
                pynvml.nvmlInit()
                self.device_count = pynvml.nvmlDeviceGetCount()
            except Exception as e:
                print(f"NVML初始化失败，切换到模拟模式: {e}")
                self.simulation_mode = True
                self.device_count = 3  # 模拟3个GPU
        else:
            self.device_count = 3  # 模拟3个GPU
    
    def get_gpu_info(self, device_id: int = 0) -> Dict:
        """
        获取指定GPU的基本信息
        
        Args:
            device_id: GPU设备ID
            
        Returns:
            GPU信息字典
        """
        if self.simulation_mode:
            return self._get_simulated_gpu_info(device_id)
        
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)
            name = pynvml.nvmlDeviceGetName(handle)
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            # 获取计算能力
            major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
            compute_capability = f"{major}.{minor}"
            
            return {
                'device_id': device_id,
                'name': name.decode() if isinstance(name, bytes) else name,
                'total_memory': memory_info.total,
                'compute_capability': compute_capability
            }
        except Exception as e:
            print(f"获取GPU信息失败: {e}")
            return self._get_simulated_gpu_info(device_id)
    
    def _get_simulated_gpu_info(self, device_id: int) -> Dict:
        """获取模拟的GPU信息"""
        gpu_models = [
            {'name': 'RTX 4090', 'memory': 24 * 1024**3, 'compute': '8.9'},
            {'name': 'A100', 'memory': 40 * 1024**3, 'compute': '8.0'},
            {'name': 'H100', 'memory': 80 * 1024**3, 'compute': '9.0'}
        ]
        
        model = gpu_models[device_id % len(gpu_models)]
        return {
            'device_id': device_id,
            'name': model['name'],
            'total_memory': model['memory'],
            'compute_capability': model['compute']
        }
    
    def get_gpu_utilization(self, device_id: int = 0) -> Dict:
        """
        获取GPU利用率信息
        
        Args:
            device_id: GPU设备ID
            
        Returns:
            利用率信息字典
        """
        if self.simulation_mode:
            return self._get_simulated_utilization(device_id)
        
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # 转换为瓦特
            
            return {
                'device_id': device_id,
                'timestamp': datetime.now().isoformat(),
                'gpu_utilization': utilization.gpu,
                'memory_utilization': (memory_info.used / memory_info.total) * 100,
                'memory_used': memory_info.used,
                'memory_total': memory_info.total,
                'memory_free': memory_info.free,
                'temperature': temperature,
                'power_usage': power
            }
        except Exception as e:
            print(f"获取GPU利用率失败: {e}")
            return self._get_simulated_utilization(device_id)
    
    def _get_simulated_utilization(self, device_id: int) -> Dict:
        """获取模拟的GPU利用率"""
        import random
        
        # 生成随机但合理的利用率数据
        base_util = 20 + (device_id * 10)
        variation = random.uniform(-10, 20)
        gpu_util = max(0, min(100, base_util + variation))
        
        info = self._get_simulated_gpu_info(device_id)
        memory_used = int(info['total_memory'] * (gpu_util / 100))
        
        return {
            'device_id': device_id,
            'timestamp': datetime.now().isoformat(),
            'gpu_utilization': round(gpu_util, 1),
            'memory_utilization': round(gpu_util * 0.8, 1),
            'memory_used': memory_used,
            'memory_total': info['total_memory'],
            'memory_free': info['total_memory'] - memory_used,
            'temperature': int(50 + gpu_util * 0.3),
            'power_usage': round(150 + gpu_util * 2, 1)
        }
    
    def get_all_gpus_status(self) -> List[Dict]:
        """
        获取所有GPU的状态信息
        
        Returns:
            所有GPU状态列表
        """
        status_list = []
        for i in range(self.device_count):
            info = self.get_gpu_info(i)
            util = self.get_gpu_utilization(i)
            
            status = {**info, **util}
            status_list.append(status)
        
        return status_list
    
    def start_monitoring(self, interval: float = 2.0):
        """
        启动GPU监控
        
        Args:
            interval: 监控间隔（秒）
        """
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止GPU监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            try:
                self.gpu_stats = {
                    'timestamp': datetime.now().isoformat(),
                    'gpus': self.get_all_gpus_status()
                }
            except Exception as e:
                print(f"监控循环错误: {e}")
            
            time.sleep(interval)
    
    def get_latest_stats(self) -> Dict:
        """获取最新的GPU统计信息"""
        if not self.gpu_stats:
            return {
                'timestamp': datetime.now().isoformat(),
                'gpus': self.get_all_gpus_status()
            }
        return self.gpu_stats
    
    def __del__(self):
        """清理资源"""
        self.stop_monitoring()
        if not self.simulation_mode:
            try:
                pynvml.nvmlShutdown()
            except:
                pass


# 示例使用
if __name__ == "__main__":
    # 创建监控器（模拟模式）
    monitor = GPUMonitor(simulation_mode=True)
    
    print("GPU设备信息:")
    for i in range(monitor.device_count):
        info = monitor.get_gpu_info(i)
        print(f"  GPU {i}: {info['name']} - {info['total_memory'] / (1024**3):.1f}GB")
    
    print("\nGPU利用率:")
    stats = monitor.get_all_gpus_status()
    for gpu in stats:
        print(f"  GPU {gpu['device_id']}: {gpu['gpu_utilization']:.1f}% "
              f"Memory: {gpu['memory_used'] / (1024**3):.1f}GB / "
              f"{gpu['memory_total'] / (1024**3):.1f}GB")
    
    # 启动监控
    print("\n启动持续监控...")
    monitor.start_monitoring(interval=2.0)
    
    try:
        for _ in range(5):
            time.sleep(2)
            latest = monitor.get_latest_stats()
            print(f"\n[{latest['timestamp']}]")
            for gpu in latest['gpus']:
                print(f"  GPU {gpu['device_id']}: {gpu['gpu_utilization']:.1f}% @ {gpu['temperature']}°C")
    finally:
        monitor.stop_monitoring()
        print("\n监控已停止")
