"""
CUDA JIT封装模块 - 将用户提交的代码封装为CUDA JIT可执行代码
"""

import numba
from numba import cuda
import numpy as np
import ast
import inspect
from typing import Callable, Any, Dict, List, Tuple


class CudaJITWrapper:
    """CUDA JIT封装器，用于将Python代码编译为CUDA核函数"""
    
    def __init__(self):
        self.compiled_kernels = {}
    
    def wrap_kernel(self, code: str, function_name: str = None) -> Callable:
        """
        将用户代码封装为CUDA JIT核函数
        
        Args:
            code: 用户提交的Python代码
            function_name: 函数名称，如果为None则自动检测
            
        Returns:
            编译后的CUDA核函数
        """
        # 解析代码，提取函数定义
        try:
            tree = ast.parse(code)
            
            # 查找函数定义
            func_defs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            
            if not func_defs:
                raise ValueError("未找到函数定义")
            
            if function_name:
                func_def = next((f for f in func_defs if f.name == function_name), None)
                if not func_def:
                    raise ValueError(f"未找到函数 {function_name}")
            else:
                func_def = func_defs[0]
                function_name = func_def.name
            
            # 执行代码以获取函数对象
            namespace = {
                'cuda': cuda,
                'numba': numba,
                'np': np,
            }
            exec(code, namespace)
            
            user_func = namespace[function_name]
            
            # 使用CUDA JIT编译
            kernel = cuda.jit(user_func)
            
            # 缓存编译后的核函数
            self.compiled_kernels[function_name] = kernel
            
            return kernel
            
        except Exception as e:
            raise RuntimeError(f"CUDA JIT编译失败: {str(e)}")
    
    def create_kernel_package(self, code: str, test_inputs: List[np.ndarray],
                            grid_size: Tuple[int, ...], block_size: Tuple[int, ...]) -> Dict[str, Any]:
        """
        创建完整的内核执行包
        
        Args:
            code: 用户代码
            test_inputs: 测试输入数据
            grid_size: CUDA Grid大小
            block_size: CUDA Block大小
            
        Returns:
            包含所有执行信息的字典
        """
        package = {
            'code': code,
            'test_inputs': [inp.tolist() if isinstance(inp, np.ndarray) else inp for inp in test_inputs],
            'grid_size': grid_size,
            'block_size': block_size,
            'input_shapes': [inp.shape if isinstance(inp, np.ndarray) else None for inp in test_inputs],
            'input_dtypes': [str(inp.dtype) if isinstance(inp, np.ndarray) else None for inp in test_inputs]
        }
        return package
    
    def execute_kernel(self, kernel: Callable, inputs: List[np.ndarray],
                      grid_size: Tuple[int, ...], block_size: Tuple[int, ...]) -> List[np.ndarray]:
        """
        执行CUDA核函数
        
        Args:
            kernel: 编译后的CUDA核函数
            inputs: 输入数据列表
            grid_size: Grid大小
            block_size: Block大小
            
        Returns:
            输出结果列表
        """
        try:
            # 将输入复制到GPU
            d_inputs = [cuda.to_device(inp) for inp in inputs]
            
            # 执行核函数
            kernel[grid_size, block_size](*d_inputs)
            
            # 同步GPU
            cuda.synchronize()
            
            # 将结果复制回CPU
            results = [d_inp.copy_to_host() for d_inp in d_inputs]
            
            return results
            
        except Exception as e:
            raise RuntimeError(f"CUDA核函数执行失败: {str(e)}")
    
    def validate_cuda_code(self, code: str) -> Tuple[bool, str]:
        """
        验证CUDA代码的有效性
        
        Args:
            code: 用户代码
            
        Returns:
            (是否有效, 错误消息)
        """
        try:
            # 语法检查
            ast.parse(code)
            
            # 检查是否包含函数定义
            tree = ast.parse(code)
            func_defs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            
            if not func_defs:
                return False, "代码中未找到函数定义"
            
            return True, "代码验证通过"
            
        except SyntaxError as e:
            return False, f"语法错误: {str(e)}"
        except Exception as e:
            return False, f"验证失败: {str(e)}"


# 示例使用
if __name__ == "__main__":
    # 创建封装器
    wrapper = CudaJITWrapper()
    
    # 示例代码：向量加法
    sample_code = """
def vector_add(a, b, c):
    idx = cuda.grid(1)
    if idx < c.size:
        c[idx] = a[idx] + b[idx]
"""
    
    # 验证代码
    is_valid, msg = wrapper.validate_cuda_code(sample_code)
    print(f"代码验证: {msg}")
    
    if is_valid:
        # 编译内核
        kernel = wrapper.wrap_kernel(sample_code, "vector_add")
        print(f"内核编译成功: {kernel}")
        
        # 准备测试数据
        n = 1000
        a = np.arange(n, dtype=np.float32)
        b = np.arange(n, dtype=np.float32)
        c = np.zeros(n, dtype=np.float32)
        
        # 执行内核
        results = wrapper.execute_kernel(kernel, [a, b, c], (32,), (32,))
        print(f"执行结果: {results[2][:10]}")  # 打印前10个结果
