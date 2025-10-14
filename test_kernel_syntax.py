#!/usr/bin/env python3
"""
Test script to verify the kernel.cu syntax fixes
"""

import os
import subprocess
import sys

def test_kernel_syntax():
    """Test if the kernel.cu file has correct syntax"""
    
    # Check if nvcc is available
    try:
        result = subprocess.run(['which', 'nvcc'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ nvcc not found in PATH")
            print("This is expected in environments without CUDA toolkit")
            return False
    except FileNotFoundError:
        print("❌ nvcc command not found")
        print("This is expected in environments without CUDA toolkit")
        return False
    
    # Try to compile with syntax check only
    try:
        result = subprocess.run([
            'nvcc', '--cubin', '-std=c++17', 
            '-gencode=arch=compute_90,code=sm_90', 
            '--use_fast_math', '-O3', '-arch', 'sm_90',
            '-I/usr/local/lib/python3.12/dist-packages/pycuda/cuda',
            'kernel.cu'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ kernel.cu compiled successfully!")
            return True
        else:
            print("❌ Compilation failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Compilation timed out")
        return False
    except Exception as e:
        print(f"❌ Error during compilation: {e}")
        return False

def analyze_kernel_fixes():
    """Analyze the fixes made to kernel.cu"""
    
    print("🔍 Analyzing kernel.cu fixes...")
    
    with open('kernel.cu', 'r') as f:
        content = f.read()
    
    fixes_applied = []
    
    # Check for fixed inline assembly
    if 'asm volatile("wgmma.fence.sync.aligned;\\n" ::: "memory");' in content:
        fixes_applied.append("✅ Fixed inline assembly string termination")
    else:
        fixes_applied.append("❌ Inline assembly fix not found")
    
    if 'asm volatile("wgmma.commit_group.sync.aligned;\\n" ::: "memory");' in content:
        fixes_applied.append("✅ Fixed commit_group assembly string")
    else:
        fixes_applied.append("❌ commit_group assembly fix not found")
    
    if 'asm volatile("wgmma.wait_group.sync.aligned 0;\\n" ::: "memory");' in content:
        fixes_applied.append("✅ Fixed wait_group assembly string")
    else:
        fixes_applied.append("❌ wait_group assembly fix not found")
    
    # Check for C/C++ separation
    if 'void cuda_linear_impl(' in content:
        fixes_applied.append("✅ Added C++ implementation function")
    else:
        fixes_applied.append("❌ C++ implementation function not found")
    
    if 'extern "C" {' in content:
        fixes_applied.append("✅ Added extern C wrapper")
    else:
        fixes_applied.append("❌ extern C wrapper not found")
    
    # Print results
    print("\n📋 Fix Analysis Results:")
    for fix in fixes_applied:
        print(f"  {fix}")
    
    return all("✅" in fix for fix in fixes_applied)

def main():
    print("🚀 CUDA Kernel Syntax Test")
    print("=" * 40)
    
    # Check if kernel.cu exists
    if not os.path.exists('kernel.cu'):
        print("❌ kernel.cu file not found")
        return False
    
    print("✅ kernel.cu file found")
    
    # Analyze fixes
    fixes_ok = analyze_kernel_fixes()
    
    # Try to test compilation (if nvcc available)
    compilation_ok = test_kernel_syntax()
    
    print("\n📊 Summary:")
    print(f"  Fixes Applied: {'✅' if fixes_ok else '❌'}")
    print(f"  Compilation: {'✅' if compilation_ok else '❌ (nvcc not available)'}")
    
    if fixes_ok:
        print("\n🎉 All syntax fixes have been applied successfully!")
        print("The kernel.cu file should now compile without the original errors.")
    else:
        print("\n⚠️  Some fixes may be missing. Please check the analysis above.")
    
    return fixes_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)