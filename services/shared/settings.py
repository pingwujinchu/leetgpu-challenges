from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_algorithm: str
    jwt_exp_minutes: int
    artifacts_dir: Path


def load_settings() -> Settings:
    repo_root = Path(os.environ.get("REPO_ROOT", Path(__file__).resolve().parents[2])).resolve()
    artifacts_dir = Path(os.environ.get("ARTIFACTS_DIR", str(repo_root / "artifacts"))).resolve()
    return Settings(
        repo_root=repo_root,
        database_url=os.environ.get("DATABASE_URL", f"sqlite:///{repo_root}/artifacts/app.db"),
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        jwt_secret=os.environ.get("JWT_SECRET", "dev-secret-change-me"),
        jwt_algorithm=os.environ.get("JWT_ALG", "HS256"),
        jwt_exp_minutes=int(os.environ.get("JWT_EXP_MINUTES", "720")),
        artifacts_dir=artifacts_dir,
    )

