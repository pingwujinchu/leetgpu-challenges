from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from services.shared.db import Base, Job, JobStatus, make_session_factory
from services.shared.settings import load_settings
from services.worker.app.executors import docker_compile_only, local_compile_only


settings = load_settings()
SessionFactory, engine = make_session_factory(settings.database_url)


def _init_db() -> None:
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def _work_dir(job_id: int) -> Path:
    return settings.artifacts_dir / "jobs" / str(job_id) / "work"

def _source_file_path(job_id: int, framework: str) -> Path:
    ext = "cu" if framework == "cuda" else "py"
    return settings.artifacts_dir / "jobs" / str(job_id) / f"solution.{ext}"


def run_job(job_id: int) -> None:
    """
    RQ task entrypoint: execute a submitted job and persist results.

    Isolation:
      - Default: docker compile-only (network off, read-only root, tmpfs)
      - Fallback: local compile-only (not strong isolation)
    """
    _init_db()
    db: Session = SessionFactory()
    try:
        job = db.get(Job, job_id)
        if not job:
            return

        if job.status in {JobStatus.cancelled, JobStatus.succeeded, JobStatus.failed}:
            return

        job.status = JobStatus.running
        job.started_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()

        if not job.source_code:
            job.status = JobStatus.failed
            job.error = "Missing source_code in DB"
            job.finished_at = datetime.now(timezone.utc)
            db.add(job)
            db.commit()
            return

        executor = (os.environ.get("JOB_EXECUTOR", "docker").strip().lower())
        wdir = _work_dir(job.id)
        wdir.mkdir(parents=True, exist_ok=True)

        # Materialize code into a local file for compilation/execution.
        src_path = _source_file_path(job.id, job.framework)
        src_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.write_text(job.source_code, encoding="utf-8")

        if executor == "docker":
            res = docker_compile_only(
                framework=job.framework,
                source_path=src_path,
                repo_root=settings.repo_root,
                work_dir=wdir,
                gpu_vendor=job.gpu_vendor,
            )
        else:
            res = local_compile_only(job.framework, src_path)

        job.exit_code = res.exit_code
        job.stdout = (res.stdout or "")[:2_000_000]
        job.stderr = (res.stderr or "")[:2_000_000]
        job.error = res.error
        job.finished_at = datetime.now(timezone.utc)
        job.status = JobStatus.succeeded if res.exit_code == 0 else JobStatus.failed
        db.add(job)
        db.commit()
    finally:
        db.close()

