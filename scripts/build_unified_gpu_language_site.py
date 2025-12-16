#!/usr/bin/env python3
"""
Build a tiny static index for a unified GPU-language website.

It scans challenges/*/*/challenge.py plus starter templates and emits:
  - static/challenges.json

No external deps. Safe to run in CI or locally.
"""

from __future__ import annotations

import ast
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
CHALLENGES_DIR = REPO_ROOT / "challenges"
OUT_JSON = REPO_ROOT / "static" / "challenges.json"


@dataclass(frozen=True)
class Framework:
    id: str
    label: str
    file_rel: str  # relative to challenge directory
    kind: str  # "cuda"|"python"


FRAMEWORKS: List[Framework] = [
    Framework(id="cuda", label="CUDA", file_rel="starter/starter.cu", kind="cuda"),
    Framework(id="triton", label="Triton", file_rel="starter/starter.triton.py", kind="python"),
    Framework(id="cute", label="CUTE DSL", file_rel="starter/starter.cute.py", kind="python"),
    # Not present in this repo yet, but the website supports it as a first-class tab.
    Framework(id="cutile", label="CuTile-Python", file_rel="starter/starter.cutile.py", kind="python"),
]


GPU_VENDOR_BY_FRAMEWORK: Dict[str, List[str]] = {
    "cuda": ["nvidia"],
    "cute": ["nvidia"],
    # Triton can target NVIDIA (CUDA) and AMD (HIP) depending on install/runtime.
    "triton": ["nvidia", "amd"],
    # Placeholder until templates land.
    "cutile": ["nvidia"],
}


def _iter_challenge_dirs(challenges_dir: Path) -> Iterable[Tuple[str, Path]]:
    """Yield (difficulty, challenge_dir)."""
    for difficulty_dir in sorted(p for p in challenges_dir.iterdir() if p.is_dir()):
        difficulty = difficulty_dir.name
        for challenge_dir in sorted(p for p in difficulty_dir.iterdir() if p.is_dir()):
            if (challenge_dir / "challenge.py").is_file() and (challenge_dir / "challenge.html").is_file():
                yield difficulty, challenge_dir


def _parse_super_init_kwargs(challenge_py: Path) -> Dict[str, Any]:
    """
    Extract keyword args from super().__init__(...) in Challenge.__init__.
    Only supports literal values (strings, ints, floats, bools, None).
    """
    src = challenge_py.read_text(encoding="utf-8")
    mod = ast.parse(src, filename=str(challenge_py))

    for node in ast.walk(mod):
        if not isinstance(node, ast.ClassDef) or node.name != "Challenge":
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef) or item.name != "__init__":
                continue
            for stmt in ast.walk(item):
                if not isinstance(stmt, ast.Call):
                    continue
                # match: super().__init__(...)
                if not isinstance(stmt.func, ast.Attribute) or stmt.func.attr != "__init__":
                    continue
                if not isinstance(stmt.func.value, ast.Call):
                    continue
                inner = stmt.func.value
                if not isinstance(inner.func, ast.Name) or inner.func.id != "super":
                    continue

                out: Dict[str, Any] = {}
                for kw in stmt.keywords:
                    if kw.arg is None:
                        continue
                    try:
                        out[kw.arg] = ast.literal_eval(kw.value)
                    except Exception:
                        # Keep the site build resilient; unknown expressions become None.
                        out[kw.arg] = None
                return out

    return {}


def _challenge_id_from_folder(folder_name: str) -> Optional[int]:
    # folder like "22_gemm"
    prefix = folder_name.split("_", 1)[0]
    try:
        return int(prefix)
    except Exception:
        return None


def _available_frameworks(challenge_dir: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for fw in FRAMEWORKS:
        p = challenge_dir / fw.file_rel
        out.append(
            {
                "id": fw.id,
                "label": fw.label,
                "kind": fw.kind,
                "path": str(p.relative_to(REPO_ROOT)).replace(os.sep, "/"),
                "exists": p.is_file(),
                "gpu_vendors": GPU_VENDOR_BY_FRAMEWORK.get(fw.id, []),
            }
        )
    return out


def build_index() -> Dict[str, Any]:
    challenges: List[Dict[str, Any]] = []

    for difficulty, challenge_dir in _iter_challenge_dirs(CHALLENGES_DIR):
        folder = challenge_dir.name
        cid = _challenge_id_from_folder(folder)
        meta = _parse_super_init_kwargs(challenge_dir / "challenge.py")

        frameworks = _available_frameworks(challenge_dir)
        gpu_vendors: List[str] = sorted(
            {v for fw in frameworks if fw["exists"] for v in fw.get("gpu_vendors", [])}
        )

        challenges.append(
            {
                "id": cid,
                "difficulty": difficulty,
                "slug": folder,
                "title": meta.get("name") or folder.replace("_", " "),
                "num_gpus": meta.get("num_gpus"),
                "access_tier": meta.get("access_tier"),
                "paths": {
                    "base": str(challenge_dir.relative_to(REPO_ROOT)).replace(os.sep, "/"),
                    "challenge_html": str((challenge_dir / "challenge.html").relative_to(REPO_ROOT)).replace(
                        os.sep, "/"
                    ),
                    "challenge_py": str((challenge_dir / "challenge.py").relative_to(REPO_ROOT)).replace(
                        os.sep, "/"
                    ),
                },
                "frameworks": frameworks,
                "gpu_vendors": gpu_vendors,
            }
        )

    challenges.sort(key=lambda c: (c["id"] is None, c["id"] or 10**9, c["difficulty"], c["slug"]))
    return {
        "schema_version": 1,
        "generated_from": "scripts/build_unified_gpu_language_site.py",
        "challenge_count": len(challenges),
        "frameworks_supported": [fw.id for fw in FRAMEWORKS],
        "gpu_vendors_supported": ["nvidia", "amd", "intel", "apple"],
        "challenges": challenges,
    }


def main() -> None:
    data = build_index()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON} ({data['challenge_count']} challenges)")


if __name__ == "__main__":
    main()

