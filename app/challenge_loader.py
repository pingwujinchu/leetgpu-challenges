import importlib.util
import inspect
import os
import hashlib
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any

CHALLENGES_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "challenges")


@dataclass
class ChallengeInfo:
    difficulty: str
    folder_name: str
    folder_path: str
    module_path: str
    slug: str  # e.g., "easy/41_simple_inference"
    name: Optional[str] = None


def _make_module_name(module_path: str) -> str:
    h = hashlib.sha1(module_path.encode("utf-8")).hexdigest()[:12]
    return f"challenge_module_{h}"


def discover_challenges(root: Optional[str] = None) -> List[ChallengeInfo]:
    root_dir = root or CHALLENGES_ROOT
    results: List[ChallengeInfo] = []
    if not os.path.isdir(root_dir):
        return results

    for difficulty in sorted(os.listdir(root_dir)):
        diff_dir = os.path.join(root_dir, difficulty)
        if not os.path.isdir(diff_dir):
            continue
        for folder_name in sorted(os.listdir(diff_dir)):
            folder_path = os.path.join(diff_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue
            module_path = os.path.join(folder_path, "challenge.py")
            if os.path.isfile(module_path):
                slug = f"{difficulty}/{folder_name}"
                results.append(ChallengeInfo(
                    difficulty=difficulty,
                    folder_name=folder_name,
                    folder_path=folder_path,
                    module_path=module_path,
                    slug=slug,
                ))
    return results


def load_challenge_instance(info: ChallengeInfo) -> Any:
    spec = importlib.util.spec_from_file_location(_make_module_name(info.module_path), info.module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module for {info.module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]

    # Expect class named "Challenge"
    if not hasattr(module, "Challenge"):
        raise RuntimeError(f"Module {info.module_path} has no Challenge class")
    cls = getattr(module, "Challenge")
    instance = cls()
    return instance


def read_challenge_html(info: ChallengeInfo) -> Optional[str]:
    html_path = os.path.join(info.folder_path, "challenge.html")
    if os.path.isfile(html_path):
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None
    return None


def get_challenge_name(instance: Any) -> Optional[str]:
    return getattr(instance, "name", None)


def get_reference_signature_params(instance: Any) -> Tuple[List[str], int]:
    # Returns (param_names, num_positional)
    fn = getattr(instance, "reference_impl", None)
    if fn is None:
        return ([], 0)
    sig = inspect.signature(fn)
    # exclude self
    params = [p for p in sig.parameters.values() if p.name != "self"]
    names = [p.name for p in params]
    num_positional = sum(1 for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD))
    return (names, num_positional)
