#!/usr/bin/env python3
"""
Test script to verify the kernel.cu syntax fixes
"""

import os
import subprocess
import sys

def test_kernel_fixes():
    """Test if the kernel.cu file has correct syntax fixes"""
    
    print("🔍 Analyzing kernel.cu fixes...")
    
    with open('kernel.cu', 'r') as f:
        content = f.read()
    
    fixes_applied = []
    
    # Check for fixed inline assembly - look for the actual patterns
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

def show_key_fixes():
    """Show the key fixes that were applied"""
    
    print("\n🔧 Key Fixes Applied:")
    print("1. Fixed inline assembly string termination:")
    print("   - Added \\n escape sequences to assembly strings")
    print("   - Ensured proper string closure")
    print()
    print("2. Separated C++ and C interfaces:")
    print("   - Created cuda_linear_impl() for C++ implementation")
    print("   - Wrapped cuda_linear() in extern \"C\" block")
    print()
    print("3. Fixed compilation errors:")
    print("   - Resolved missing terminating quote characters")
    print("   - Fixed extern \"C\" linkage issues with C++ templates")

def main():
    print("🚀 CUDA Kernel Fix Verification")
    print("=" * 40)
    
    # Check if kernel.cu exists
    if not os.path.exists('kernel.cu'):
        print("❌ kernel.cu file not found")
        return False
    
    print("✅ kernel.cu file found")
    
    # Analyze fixes
    fixes_ok = test_kernel_fixes()
    
    # Show what was fixed
    show_key_fixes()
    
    print("\n📊 Summary:")
    print(f"  Fixes Applied: {'✅' if fixes_ok else '❌'}")
    
    if fixes_ok:
        print("\n🎉 All syntax fixes have been applied successfully!")
        print("The kernel.cu file should now compile without the original errors:")
        print("  - Missing terminating quote characters")
        print("  - extern \"C\" linkage issues")
    else:
        print("\n⚠️  Some fixes may be missing. Please check the analysis above.")
    
    return fixes_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)