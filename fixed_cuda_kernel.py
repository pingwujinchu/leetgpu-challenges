"""
CUDA Quantize to Int8 Kernel - Fixed Implementation

This module implements a fixed CUDA kernel for quantize to int8.
The main fixes:
1. Fixed inline assembly string termination issues
2. Resolved extern "C" linkage problems by separating C++ and C interfaces
"""

import torch
import torch.nn.functional as F
import numpy as np
from vllm import _custom_ops as ops
import time
import statistics

try:
    import pycuda.driver as cuda
    import pycuda.autoinit
    from pycuda.compiler import SourceModule
    import pycuda.gpuarray as gpuarray
    CUDA_AVAILABLE = True
except ImportError:
    CUDA_AVAILABLE = False
    print("PyCUDA not available, using CPU fallback")

import os
os.environ["TORCH_CUDA_ARCH_LIST"] = "9.0a"  # Hopper / sm_90a

import torch
import torch.utils.cpp_extension as torch_cpp_ext
import torch.nn.functional as F


# Fixed CUDA kernel source
cuda_kernel_source = """
#include <cuda.h>
#include <cuda_runtime.h>
#include <cuda/barrier>
#include <cuda/ptx>
#include <cuda_fp16.h>
#include <torch/extension.h>
#include <c10/cuda/CUDAStream.h>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <type_traits>

using barrier = cuda::barrier<cuda::thread_scope_block>;
namespace cde = cuda::device::experimental;

__device__ __forceinline__ uint64_t enc16B(uint64_t x) { return (x & 0x3FFFF) >> 4; }

template<int BM, int BN, int BK, int NUM_THREADS>
__global__ void __launch_bounds__(NUM_THREADS) m64n8k16(
        int M, int N, int K, __half* C, 
        const __grid_constant__ CUtensorMap tensorMapA,
        const __grid_constant__ CUtensorMap tensorMapB) {

    __shared__ alignas(128) __half sA[BM * BK];
    __shared__ alignas(128) __half sB[BK * BN];

    float d[4] = {0.f};

    #pragma nv_diag_suppress static_var_with_dynamic_init
    __shared__ barrier bar;

    if (threadIdx.x == 0) {
        init(&bar, blockDim.x);
        cde::fence_proxy_async_shared_cta();
    }
    __syncthreads();

    barrier::arrival_token token;
    // Load by TMA
    if (threadIdx.x == 0) {
        cde::cp_async_bulk_tensor_2d_global_to_shared(sA, &tensorMapA, 0, 0, bar);
        cde::cp_async_bulk_tensor_2d_global_to_shared(sB, &tensorMapB, 0, 0, bar);
        token = cuda::device::barrier_arrive_tx(bar, 1, sizeof(sA) + sizeof(sB));
    } else {
        token = bar.arrive();
    }
    bar.wait(std::move(token));
    __syncthreads();

    // Compute by WGMMA (FP16) - Fixed inline assembly strings
    asm volatile("wgmma.fence.sync.aligned;\\n" ::: "memory");

    uint64_t sa_addr = (uint64_t)sA;
    uint64_t sb_addr = (uint64_t)sB;

    uint64_t swizzle  = CUtensorMapSwizzle::CU_TENSOR_MAP_SWIZZLE_NONE;

    // ===== A descriptor: m64k16 (64×16 half K-major) =====
    uint64_t desc_a = 0;
    desc_a |= enc16B((uint64_t)sa_addr);
    desc_a |= enc16B((uint64_t)128) << 16;
    desc_a |= enc16B((uint64_t)256) << 32;
    desc_a |= swizzle << 62;

    // ===== B descriptor: n8k16 (8×16 half K-major) =====
    uint64_t desc_b = 0;
    desc_b |= enc16B((uint64_t)sb_addr);
    desc_b |= enc16B((uint64_t)128) << 16;
    desc_b |= enc16B((uint64_t)128) << 32;
    desc_b |= swizzle << 62;

    asm volatile(
        "wgmma.mma_async.sync.aligned.m64n8k16.f32.f16.f16 {%0,%1,%2,%3}, %4, %5, 1, 1, 1, 0, 0;"
        : "+f"(d[0]), "+f"(d[1]), "+f"(d[2]), "+f"(d[3]) : "l"(desc_a), "l"(desc_b));

    asm volatile("wgmma.commit_group.sync.aligned;\\n" ::: "memory");
    asm volatile("wgmma.wait_group.sync.aligned 0;\\n" ::: "memory");

    {
        int tid  = threadIdx.x;
        int lane = tid % 32;
        int warp = tid / 32;
        int row  = warp * 16 + lane / 4;
        int col  = 2 * (lane % 4);

        C[((row    ) * N + (col    ))] = __float2half_rn(d[0]);
        C[((row    ) * N + (col + 1))] = __float2half_rn(d[1]);
        C[((row + 8) * N + (col    ))] = __float2half_rn(d[2]);
        C[((row + 8) * N + (col + 1))] = __float2half_rn(d[3]);
    }
}

// C++ implementation function
void cuda_linear_impl(torch::Tensor A, torch::Tensor B, torch::Tensor C, int M, int N, int K) {
    constexpr int BM = 64;
    constexpr int BN = 8;
    constexpr int BK = 16;
    constexpr int NUM_THREADS = 128;

    auto *Aptr = reinterpret_cast<__half*>(A.data_ptr<c10::Half>());
    auto *Bptr = reinterpret_cast<__half*>(B.data_ptr<c10::Half>());
    auto *Cptr = reinterpret_cast<__half*>(C.data_ptr<c10::Half>());

    CUtensorMap tmaA{};
    {
        constexpr uint32_t rank    = 2;
        uint64_t size[rank]        = {16, 64};                  // {K, M}
        uint64_t stride[rank - 1]  = {16ull * sizeof(__half)};  // 32 bytes
        uint32_t box[rank]         = {16, 64};                  // Load full A 64x16
        uint32_t elem_stride[rank] = {1, 1};

        CUresult res = cuTensorMapEncodeTiled(
            &tmaA,
            CU_TENSOR_MAP_DATA_TYPE_FLOAT16,
            rank,
            Aptr,        // Point to A[0,0]
            size,
            stride,
            box,
            elem_stride,
            CUtensorMapInterleave::CU_TENSOR_MAP_INTERLEAVE_NONE,
            CUtensorMapSwizzle::CU_TENSOR_MAP_SWIZZLE_NONE,
            CUtensorMapL2promotion::CU_TENSOR_MAP_L2_PROMOTION_NONE,
            CUtensorMapFloatOOBfill::CU_TENSOR_MAP_FLOAT_OOB_FILL_NONE
        );
    }

    CUtensorMap tmaB{};
    {
        constexpr uint32_t rank    = 2;
        uint64_t size[rank]        = {16, 8};                   // {K, N}
        uint64_t stride[rank - 1]  = {16ull * sizeof(__half)};  // 16 bytes
        uint32_t box[rank]         = {16, 8};                   // Load full B 8x16
        uint32_t elem_stride[rank] = {1, 1};

        CUresult res = cuTensorMapEncodeTiled(
            &tmaB,
            CU_TENSOR_MAP_DATA_TYPE_FLOAT16,
            rank,
            Bptr,        // Point to B[0,0]
            size,
            stride,
            box,
            elem_stride,
            CUtensorMapInterleave::CU_TENSOR_MAP_INTERLEAVE_NONE,
            CUtensorMapSwizzle::CU_TENSOR_MAP_SWIZZLE_NONE,
            CUtensorMapL2promotion::CU_TENSOR_MAP_L2_PROMOTION_NONE,
            CUtensorMapFloatOOBfill::CU_TENSOR_MAP_FLOAT_OOB_FILL_NONE
        );
    }

    const dim3 grid(1);
    const dim3 block(NUM_THREADS);
    m64n8k16<BM, BN, BK, NUM_THREADS><<<grid, block>>>(M, N, K, Cptr, tmaA, tmaB);
}

// C interface function
extern "C" {
    void cuda_linear(torch::Tensor A, torch::Tensor B, torch::Tensor C, int M, int N, int K) {
        cuda_linear_impl(A, B, C, M, N, K);
    }
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("cuda_linear", &cuda_linear, "linear (FP16 only, WGMMA+TMA, no cache, no inline)");
}
"""

def cuda_mm(input_tensor, weight):
    """
    Perform matrix multiplication using CUDA kernel.
    
    Args:
        input_tensor: Input tensor of shape (M, K)
        weight: Weight tensor of shape (K, N)
        
    Returns:
        Output tensor of shape (M, N)
    """
    if not CUDA_AVAILABLE:
        # Fallback to PyTorch implementation
        return torch.matmul(input_tensor, weight)
    
    # Get matrix dimensions
    M, K = input_tensor.shape
    N = weight.shape[1]
    
    # Ensure tensors are on GPU and in float16
    if input_tensor.device.type != 'cuda':
        input_tensor = input_tensor.cuda()
    if weight.device.type != 'cuda':
        weight = weight.cuda()
    
    # Convert to float16 if needed
    if input_tensor.dtype != torch.float16:
        input_tensor = input_tensor.half()
    if weight.dtype != torch.float16:
        weight = weight.half()
    
    # Allocate output tensor
    output_tensor = torch.empty(M, N, device='cuda', dtype=torch.float16)
    
    # Compile CUDA kernel with proper compiler options
    mod = SourceModule(cuda_kernel_source, options=[
        '-std=c++17', 
        '-gencode=arch=compute_90,code=sm_90', 
        '--use_fast_math', 
        '-O3'
    ])
    
    # Get kernel functions
    kernel_func = mod.get_function("cuda_linear")
    
    # Launch kernel
    kernel_func(
        input_tensor, weight, output_tensor, M, N, K
    )
    
    return output_tensor


def matmul_reference(input_tensor, weight):
    """
    Reference implementation using PyTorch for correctness checking.
    """
    return torch.matmul(input_tensor, weight)


def benchmark_function(func, *args, num_runs=100, warmup_runs=10):
    """
    Benchmark a function with warmup and multiple runs.
    
    Args:
        func: Function to benchmark
        *args: Arguments to pass to the function
        num_runs: Number of benchmark runs
        warmup_runs: Number of warmup runs
        
    Returns:
        Dictionary with timing statistics
    """
    # Warmup runs
    for _ in range(warmup_runs):
        result = func(*args)
        torch.cuda.synchronize()  # Ensure GPU operations complete
    
    # Benchmark runs
    times = []
    for _ in range(num_runs):
        torch.cuda.synchronize()  # Ensure clean state
        start_time = time.time()
        result = func(*args)
        torch.cuda.synchronize()  # Ensure GPU operations complete
        end_time = time.time()
        times.append(end_time - start_time)
    
    return {
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'std': statistics.stdev(times) if len(times) > 1 else 0,
        'min': min(times),
        'max': max(times),
        'times': times
    }


def run_benchmark():
    """
    Run comprehensive benchmark comparing cuda_mm and matmul_reference.
    """
    print("CUDA Matrix Multiplication Benchmark")
    print("=" * 50)
    
    # Test different matrix sizes
    test_cases = [
        (64, 8, 16),    # Small case matching kernel dimensions
        (128, 64, 32),  # Medium case
        (256, 128, 64), # Large case
        (512, 256, 128), # Very large case
    ]
    
    for M, N, K in test_cases:
        print(f"\nMatrix dimensions: M={M}, N={N}, K={K}")
        print("-" * 30)
        
        # Create test matrices
        input_tensor = torch.randn(M, K, device='cuda', dtype=torch.float16)
        weight = torch.randn(K, N, device='cuda', dtype=torch.float16)
        
        # Benchmark CUDA implementation
        print("Benchmarking CUDA implementation...")
        try:
            cuda_stats = benchmark_function(cuda_mm, input_tensor, weight, num_runs=50, warmup_runs=5)
            print(f"CUDA MM - Mean: {cuda_stats['mean']*1000:.3f}ms, "
                  f"Median: {cuda_stats['median']*1000:.3f}ms, "
                  f"Std: {cuda_stats['std']*1000:.3f}ms")
        except Exception as e:
            print(f"CUDA implementation failed: {e}")
            cuda_stats = None
        
        # Benchmark reference implementation
        print("Benchmarking PyTorch reference...")
        ref_stats = benchmark_function(matmul_reference, input_tensor, weight, num_runs=50, warmup_runs=5)
        print(f"PyTorch MM - Mean: {ref_stats['mean']*1000:.3f}ms, "
              f"Median: {ref_stats['median']*1000:.3f}ms, "
              f"Std: {ref_stats['std']*1000:.3f}ms")
        
        # Calculate speedup
        if cuda_stats:
            speedup = ref_stats['mean'] / cuda_stats['mean']
            print(f"Speedup: {speedup:.2f}x")
            
            # Calculate theoretical performance
            flops = 2 * M * N * K  # 2 operations per multiply-add
            cuda_gflops = (flops / 1e9) / cuda_stats['mean']
            ref_gflops = (flops / 1e9) / ref_stats['mean']
            print(f"Performance - CUDA: {cuda_gflops:.2f} GFLOPS, PyTorch: {ref_gflops:.2f} GFLOPS")
        
        # Check correctness
        if cuda_stats:
            try:
                result_cuda = cuda_mm(input_tensor, weight)
                result_ref = matmul_reference(input_tensor, weight)
                diff = torch.abs(result_cuda - result_ref).max()
                print(f"Max difference: {diff.item():.2e}")
            except Exception as e:
                print(f"Correctness check failed: {e}")


def run_mm():
    """
    Run a simple test of the matrix multiplication function.
    """
    print("Simple Matrix Multiplication Test")
    print("=" * 40)
    
    # Create test matrices
    M = 64
    N = 8
    K = 16

    input_tensor = torch.randn(M, K, device='cuda', dtype=torch.float16)
    weight = torch.randn(K, N, device='cuda', dtype=torch.float16)

    print(f"Input shape: {input_tensor.shape}")
    print(f"Weight shape: {weight.shape}")
    
    # Run CUDA implementation
    print("\nRunning CUDA implementation...")
    try:
        result_cuda = cuda_mm(input_tensor, weight)
        print(f"CUDA result shape: {result_cuda.shape}")
    except Exception as e:
        print(f"CUDA implementation failed: {e}")
        result_cuda = None
    
    # Run reference implementation
    print("Running PyTorch reference...")
    result_ref = matmul_reference(input_tensor, weight)
    print(f"PyTorch result shape: {result_ref.shape}")
    
    # Check correctness
    if result_cuda is not None:
        diff = torch.abs(result_cuda - result_ref).max()
        print(f"Maximum difference: {diff.item():.10f}")
        
        # Check if results are close
        if diff.item() < 1e-3:
            print("✓ Results match within tolerance")
        else:
            print("✗ Results differ significantly")
    
    return result_cuda


if __name__ == "__main__":
    # Run simple test first
    result = run_mm()
    
    print("\n" + "="*60)
    
    # Run comprehensive benchmark
    run_benchmark()