from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from redis import Redis
from rq import Queue
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.schemas import (
    JobDetailResponse,
    JobResponse,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    SubmitJobRequest,
    TokenResponse,
)
from services.shared import auth as authlib
from services.shared.db import Base, Job, JobStatus, Tenant, User, UserRole, make_session_factory
from services.shared.queueing import QueueNames
from services.shared.settings import load_settings


settings = load_settings()
SessionFactory, engine = make_session_factory(settings.database_url)

IMAGE_ROOT = Path(__file__).resolve().parents[4]  # /app inside container image


def init_db() -> None:
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()


def get_redis() -> Redis:
    return Redis.from_url(settings.redis_url)


def _bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2:
        return None
    if parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
) -> User:
    token = _bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    try:
        payload = authlib.decode_token(token, secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    sub = payload.get("sub")
    tenant_name = payload.get("tenant")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    username = sub
    if ":" in sub:
        maybe_tenant, maybe_user = sub.split(":", 1)
        tenant_name = tenant_name or maybe_tenant
        username = maybe_user
    if not tenant_name:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing tenant in token")

    q = db.execute(
        select(User)
        .join(Tenant, Tenant.id == User.tenant_id)
        .where(Tenant.name == tenant_name, User.username == username)
    )
    user = q.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


app = FastAPI(title="LeetGPU Task API", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    init_db()
    # One-binary deployment: serve the unified website + challenge assets from this API process.
    # - /          -> repo_root/index.html
    # - /static/*  -> repo_root/static/*
    # - /challenges/* -> repo_root/challenges/*
    # Prefer the mounted repo_root; fall back to files shipped in the image.
    static_dir = (settings.repo_root / "static") if (settings.repo_root / "static").is_dir() else (IMAGE_ROOT / "static")
    challenges_dir = (
        (settings.repo_root / "challenges")
        if (settings.repo_root / "challenges").is_dir()
        else (IMAGE_ROOT / "challenges")
    )
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    if challenges_dir.is_dir():
        app.mount("/challenges", StaticFiles(directory=str(challenges_dir)), name="challenges")


@app.get("/", include_in_schema=False)
def web_root():
    index_path = settings.repo_root / "index.html"
    if not index_path.is_file():
        index_path = IMAGE_ROOT / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="index.html not found (neither mounted repo root nor image)")
    return FileResponse(str(index_path))


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}


@app.post("/auth/register", response_model=MeResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)) -> MeResponse:
    tenant_name = req.tenant.strip()
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Invalid username")
    if not tenant_name:
        raise HTTPException(status_code=400, detail="Invalid tenant")

    tenant = db.execute(select(Tenant).where(Tenant.name == tenant_name)).scalar_one_or_none()
    if not tenant:
        tenant = Tenant(name=tenant_name)
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    existing = (
        db.execute(select(User).where(User.tenant_id == tenant.id, User.username == username))
        .scalar_one_or_none()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        tenant_id=tenant.id,
        username=username,
        password_hash=authlib.hash_password(req.password),
        role=UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return MeResponse(
        id=user.id,
        tenant=tenant.name,
        username=user.username,
        role=user.role.value,
        created_at=user.created_at,
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    tenant_name = req.tenant.strip()
    username = req.username.strip()
    tenant = db.execute(select(Tenant).where(Tenant.name == tenant_name)).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = db.execute(select(User).where(User.tenant_id == tenant.id, User.username == username)).scalar_one_or_none()
    if not user or not authlib.verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = authlib.create_access_token(
        subject=f"{tenant.name}:{user.username}",
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.jwt_exp_minutes,
        extra_claims={"role": user.role.value, "tenant": tenant.name},
    )
    return TokenResponse(access_token=token)


@app.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeResponse:
    tenant = db.execute(select(Tenant).where(Tenant.id == user.tenant_id)).scalar_one()
    return MeResponse(
        id=user.id,
        tenant=tenant.name,
        username=user.username,
        role=user.role.value,
        created_at=user.created_at,
    )


def _validate_challenge_exists(challenge_key: str) -> Path:
    # challenge_key: "easy/1_vector_add"
    rel = Path("challenges") / challenge_key
    abs_path = (settings.repo_root / rel).resolve()
    if not abs_path.exists():
        abs_path = (IMAGE_ROOT / rel).resolve()
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail=f"Challenge not found: {challenge_key}")
    if not (abs_path / "challenge.py").is_file() or not (abs_path / "challenge.html").is_file():
        raise HTTPException(status_code=400, detail=f"Invalid challenge directory: {challenge_key}")
    return abs_path


def _artifact_path_for_job(job_id: int, framework: str) -> Path:
    ext = "cu" if framework == "cuda" else "py"
    return settings.artifacts_dir / "jobs" / str(job_id) / f"solution.{ext}"


@app.post("/jobs", response_model=JobResponse)
def submit_job(
    req: SubmitJobRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    user: User = Depends(get_current_user),
) -> JobResponse:
    _validate_challenge_exists(req.challenge_key)

    job = Job(
        tenant_id=user.tenant_id,
        user_id=user.id,
        challenge_key=req.challenge_key,
        framework=req.framework,
        gpu_vendor=req.gpu_vendor,
        gpu_arch=req.gpu_arch,
        source_code=req.source_code,
        source_path=None,
        status=JobStatus.queued,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Optional: keep a local artifact copy for debugging (not required for worker execution).
    if os.environ.get("STORE_SOURCE_ARTIFACT", "").strip().lower() in {"1", "true", "yes"}:
        src_path = _artifact_path_for_job(job.id, req.framework)
        src_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.write_text(req.source_code, encoding="utf-8")
        job.source_path = str(src_path.relative_to(settings.repo_root)).replace(os.sep, "/")
        db.add(job)
        db.commit()

    # Enqueue by vendor queue name.
    qnames = QueueNames()
    q = Queue(name=qnames.for_vendor(req.gpu_vendor), connection=redis)
    q.enqueue("services.worker.app.tasks.run_job", job.id, job_timeout="1h")

    return JobResponse(
        id=job.id,
        challenge_key=job.challenge_key,
        framework=job.framework,
        gpu_vendor=job.gpu_vendor,
        gpu_arch=job.gpu_arch,
        status=job.status.value,
        queued_at=job.queued_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        exit_code=job.exit_code,
    )


@app.get("/jobs", response_model=list[JobResponse])
def list_jobs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[JobResponse]:
    if user.role == UserRole.admin:
        rows = db.execute(select(Job).order_by(Job.id.desc())).scalars().all()
    else:
        rows = db.execute(select(Job).where(Job.user_id == user.id).order_by(Job.id.desc())).scalars().all()
    return [
        JobResponse(
            id=j.id,
            challenge_key=j.challenge_key,
            framework=j.framework,
            gpu_vendor=j.gpu_vendor,
            gpu_arch=j.gpu_arch,
            status=j.status.value,
            queued_at=j.queued_at,
            started_at=j.started_at,
            finished_at=j.finished_at,
            exit_code=j.exit_code,
        )
        for j in rows
    ]


@app.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobDetailResponse:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if user.role != UserRole.admin and job.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return JobDetailResponse(
        id=job.id,
        challenge_key=job.challenge_key,
        framework=job.framework,
        gpu_vendor=job.gpu_vendor,
        gpu_arch=job.gpu_arch,
        status=job.status.value,
        queued_at=job.queued_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        exit_code=job.exit_code,
        stdout=job.stdout,
        stderr=job.stderr,
        error=job.error,
    )

