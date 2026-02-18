from typing import List, Optional
import subprocess
import os


def list_visible_cuda_devices() -> List[int]:
    env = os.environ.get("CUDA_VISIBLE_DEVICES")
    if env is None or env.strip() == "":
        # Assume all devices are visible via nvidia-smi
        try:
            result = subprocess.run([
                "nvidia-smi", "--query-gpu=index", "--format=csv,noheader"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True, timeout=5)
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            return [int(x) for x in lines]
        except Exception:
            return []
    # Map visible device ordinals based on env order
    ords = []
    for part in env.split(","):
        part = part.strip()
        if part.isdigit():
            ords.append(int(part))
    # Expose as 0..len-1 logical indices
    return list(range(len(ords)))


def get_gpu_names() -> List[str]:
    try:
        result = subprocess.run([
            "nvidia-smi", "--query-gpu=name", "--format=csv,noheader"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True, timeout=5)
        return [l.strip() for l in result.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def cuda_device_count() -> int:
    return len(list_visible_cuda_devices())


def gpu_summary() -> List[dict]:
    indices = list_visible_cuda_devices()
    names = get_gpu_names()
    items = []
    for i, idx in enumerate(indices):
        name = names[idx] if idx < len(names) else f"GPU {idx}"
        items.append({"index": i, "physical_index": idx, "name": name})
    return items
