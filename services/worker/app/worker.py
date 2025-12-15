from __future__ import annotations

import os
import sys

from redis import Redis
from rq import Connection, Worker

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

    with Connection(redis):
        w = Worker(queues)
        w.work(with_scheduler=False)


if __name__ == "__main__":
    main()

