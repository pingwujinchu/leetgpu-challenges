from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    error: Optional[str] = None


def _safe_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = {
        # Keep environment small and deterministic.
        "PATH": os.environ.get("PATH", ""),
        "PYTHONUNBUFFERED": "1",
    }
    if extra:
        env.update(extra)
    return env


def local_compile_only(framework: str, source_path: Path) -> ExecResult:
    """
    Minimal fallback executor: performs a compile/syntax check only.
    This is NOT strong isolation; use container/sandbox execution in production.
    """
    if framework in {"triton", "cute", "cutile"}:
        cmd = ["python3", "-m", "py_compile", str(source_path)]
    elif framework == "cuda":
        nvcc = os.environ.get("NVCC_BIN", "nvcc")
        out = source_path.parent / "solution.o"
        cmd = [nvcc, "-c", str(source_path), "-o", str(out)]
    else:
        return ExecResult(exit_code=1, stdout="", stderr="", error=f"Unknown framework: {framework}")

    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=_safe_env())
    except FileNotFoundError as e:
        if framework == "cuda":
            return ExecResult(exit_code=1, stdout="", stderr="", error=f"nvcc not found: {e}")
        return ExecResult(exit_code=1, stdout="", stderr="", error=str(e))
    return ExecResult(exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr)


def docker_execute(
    *,
    image: str,
    repo_root: Path,
    work_dir: Path,
    command: List[str],
    timeout_seconds: int = 3600,
    enable_gpu: bool = False,
    gpu_vendor: str = "any",
) -> ExecResult:
    """
    Run inside Docker with basic isolation flags.
    Notes:
      - GPU enablement depends on the host runtime (e.g. nvidia-container-toolkit).
      - We keep networking disabled and filesystem read-only where possible.
    """
    if not image:
        return ExecResult(exit_code=1, stdout="", stderr="", error="Docker image not configured")

    docker = os.environ.get("DOCKER_BIN", "docker")
    base_cmd: List[str] = [
        docker,
        "run",
        "--rm",
        "--network",
        "none",
        "--pids-limit",
        "256",
        "--memory",
        os.environ.get("JOB_MEMORY", "4g"),
        "--cpus",
        os.environ.get("JOB_CPUS", "2"),
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=512m",
        "--tmpfs",
        "/var/tmp:rw,noexec,nosuid,size=512m",
        "-v",
        f"{repo_root}:/repo:ro",
        "-v",
        f"{work_dir}:/work:rw",
        "-w",
        "/work",
    ]

    if enable_gpu:
        v = (gpu_vendor or "any").lower()
        if v == "nvidia":
            # Requires nvidia-container-toolkit on the host.
            base_cmd += ["--gpus", "all"]
        # AMD/Intel GPU container enabling is environment-specific; keep as no-op by default.

    full_cmd = base_cmd + [image] + command

    try:
        p = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout_seconds, env=_safe_env())
        return ExecResult(exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except FileNotFoundError:
        return ExecResult(exit_code=1, stdout="", stderr="", error=f"Docker not found: {docker}")
    except subprocess.TimeoutExpired as e:
        return ExecResult(
            exit_code=124,
            stdout=e.stdout or "",
            stderr=e.stderr or "",
            error=f"Timed out after {timeout_seconds}s",
        )


def docker_compile_only(
    *,
    framework: str,
    source_path: Path,
    repo_root: Path,
    work_dir: Path,
    gpu_vendor: str,
) -> ExecResult:
    """
    Default container command: compile/syntax check within isolation.

    You can override images via env:
      - IMAGE_PYTHON (for python frameworks)
      - IMAGE_CUDA (for CUDA)
    """
    fw = framework.lower()
    if fw in {"triton", "cute", "cutile"}:
        image = os.environ.get("IMAGE_PYTHON", "python:3.11-slim")
        # Copy source into /work for compile (host work_dir is writable volume).
        command = [
            "bash",
            "-lc",
            f"cp -f {shlex.quote(str(source_path))} ./solution.py && python3 -m py_compile ./solution.py",
        ]
        return docker_execute(
            image=image,
            repo_root=repo_root,
            work_dir=work_dir,
            command=command,
            enable_gpu=False,
            gpu_vendor=gpu_vendor,
        )

    if fw == "cuda":
        image = os.environ.get("IMAGE_CUDA", "")
        if not image:
            return ExecResult(
                exit_code=1,
                stdout="",
                stderr="",
                error="IMAGE_CUDA is not set. Provide a CUDA build image (e.g. nvidia/cuda:12.4.1-devel-ubuntu22.04).",
            )
        command = [
            "bash",
            "-lc",
            f"cp -f {shlex.quote(str(source_path))} ./solution.cu && "
            "command -v nvcc >/dev/null 2>&1 && nvcc -c ./solution.cu -o ./solution.o",
        ]
        return docker_execute(
            image=image,
            repo_root=repo_root,
            work_dir=work_dir,
            command=command,
            enable_gpu=False,
            gpu_vendor=gpu_vendor,
        )

    return ExecResult(exit_code=1, stdout="", stderr="", error=f"Unknown framework: {framework}")

