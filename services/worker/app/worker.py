from __future__ import annotations

import os
import sys
from pathlib import Path

from redis import Redis
from rq import Worker

# When running inside containers or with varying working directories,
# ensure the repository root (containing the `services/` package) is importable.
# This also avoids relying on `python -m services....` module resolution.
_repo_root = Path(__file__).resolve().parents[4]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from services.shared.queueing import QueueNames
from services.shared.settings import load_settings


def main() -> None:
    """
    Start an RQ worker.

    Env:
      - REDIS_URL
      - WORKER_VENDOR: nvidia|amd|intel|cpu|any  (maps to jobs:<vendor>)
      - WORKER_QUEUES: comma-separated queue names (overrides WORKER_VENDOR)
      - JOB_EXECUTOR: docker|local
    """
    settings = load_settings()
    redis = Redis.from_url(settings.redis_url)

    explicit = os.environ.get("WORKER_QUEUES", "").strip()
    if explicit:
        queues = [q.strip() for q in explicit.split(",") if q.strip()]
    else:
        vendor = os.environ.get("WORKER_VENDOR", "any").strip().lower()
        queues = [QueueNames().for_vendor(vendor)]

    if not queues:
        print("No queues configured. Set WORKER_VENDOR or WORKER_QUEUES.", file=sys.stderr)
        sys.exit(2)

    # RQ v2.x no longer exposes Connection in rq.__init__.
    # Passing the connection explicitly keeps us compatible across versions.
    w = Worker(queues, connection=redis)
    w.work(with_scheduler=False)


if __name__ == "__main__":
    main()

