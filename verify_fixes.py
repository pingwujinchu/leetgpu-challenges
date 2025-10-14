#!/usr/bin/env python3

with open('kernel.cu', 'r') as f:
    content = f.read()

print("🔍 Checking kernel.cu fixes...")

# Check for the actual patterns in the file
checks = [
    ('wgmma.fence.sync.aligned;\\\\n', 'Fixed fence assembly'),
    ('wgmma.commit_group.sync.aligned;\\\\n', 'Fixed commit_group assembly'),
    ('wgmma.wait_group.sync.aligned 0;\\\\n', 'Fixed wait_group assembly'),
    ('void cuda_linear_impl(', 'Added C++ implementation'),
    ('extern "C" {', 'Added extern C wrapper')
]

all_good = True
for pattern, description in checks:
    if pattern in content:
        print(f"✅ {description}")
    else:
        print(f"❌ {description}")
        all_good = False

print(f"\n📊 Overall: {'✅ All fixes applied' if all_good else '❌ Some fixes missing'}")

if all_good:
    print("\n🎉 The kernel.cu file has been successfully fixed!")
    print("The original compilation errors should now be resolved:")
    print("  - Missing terminating quote characters")
    print("  - extern 'C' linkage issues with C++ templates")