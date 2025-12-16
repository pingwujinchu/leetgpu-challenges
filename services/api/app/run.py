from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


# When started as a file (python /path/to/run.py), sys.path[0] is the script folder.
# Ensure the package root (containing `services/`) is importable regardless of CWD/PYTHONPATH.
_pkg_root = Path(__file__).resolve().parents[3]  # /app (in image) or /repo (if mounted)
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("services.api.app.main:app", host=host, port=port, log_level=os.environ.get("LOG_LEVEL", "info"))


if __name__ == "__main__":
    main()

