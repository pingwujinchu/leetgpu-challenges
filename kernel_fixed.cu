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

    // Compute by WGMMA (FP16)
    asm volatile("wgmma.fence.sync.aligned;\n" ::: "memory");

    uint64_t sa_addr = (uint64_t)sA;
    uint64_t sb_addr = (uint64_t)sB;

    uint64_t swizzle  = CUtensorMapSwizzle::CU_TENSOR_MAP_SWIZZLE_NONE;

    // ===== A 描述符：m64k16（64×16 half K-major）=====
    uint64_t desc_a = 0;
    desc_a |= enc16B((uint64_t)sa_addr);
    desc_a |= enc16B((uint64_t)128) << 16;
    desc_a |= enc16B((uint64_t)256) << 32;
    desc_a |= swizzle << 62;

    // ===== B 描述符：n8k16（8×16 half K-major）=====
    uint64_t desc_b = 0;
    desc_b |= enc16B((uint64_t)sb_addr);
    desc_b |= enc16B((uint64_t)128) << 16;
    desc_b |= enc16B((uint64_t)128) << 32;
    desc_b |= swizzle << 62;

    asm volatile(
        "wgmma.mma_async.sync.aligned.m64n8k16.f32.f16.f16 {%0,%1,%2,%3}, %4, %5, 1, 1, 1, 0, 0;"
        : "+f"(d[0]), "+f"(d[1]), "+f"(d[2]), "+f"(d[3]) : "l"(desc_a), "l"(desc_b));

    asm volatile("wgmma.commit_group.sync.aligned;\n" ::: "memory");
    asm volatile("wgmma.wait_group.sync.aligned 0;\n" ::: "memory");

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

extern "C" {
    void cuda_linear(torch::Tensor A, torch::Tensor B, torch::Tensor C, int M, int N, int K) {
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
            uint32_t box[rank]         = {16, 64};                  // 一次搬满 A 的 64x16
            uint32_t elem_stride[rank] = {1, 1};

            CUresult res = cuTensorMapEncodeTiled(
                &tmaA,
                CU_TENSOR_MAP_DATA_TYPE_FLOAT16,
                rank,
                Aptr,        // 指向 A[0,0]
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
            uint32_t box[rank]         = {16, 8};                   // 一次搬满 B 的 8x16
            uint32_t elem_stride[rank] = {1, 1};

            CUresult res = cuTensorMapEncodeTiled(
                &tmaB,
                CU_TENSOR_MAP_DATA_TYPE_FLOAT16,
                rank,
                Bptr,        // 指向 B[0,0]
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
}

PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
    m.def("cuda_linear", &cuda_linear, "linear (FP16 only, WGMMA+TMA, no cache, no inline)");
}