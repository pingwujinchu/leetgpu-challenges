from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: datetime


class SubmitJobRequest(BaseModel):
    # challenge_key is repo-relative without leading "challenges/"
    # e.g. "easy/1_vector_add"
    challenge_key: str = Field(min_length=3, max_length=256)
    framework: Literal["cuda", "triton", "cute", "cutile"]

    # For routing
    gpu_vendor: Literal["nvidia", "amd", "intel", "apple", "cpu", "any"] = "any"
    gpu_arch: Optional[str] = Field(default=None, max_length=64)

    # User code to execute. The worker decides how to compile/run per framework.
    source_code: str = Field(min_length=1, max_length=2_000_000)


class JobResponse(BaseModel):
    id: int
    challenge_key: str
    framework: str
    gpu_vendor: str
    gpu_arch: Optional[str]
    status: str
    queued_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    exit_code: Optional[int]


class JobDetailResponse(JobResponse):
    stdout: Optional[str]
    stderr: Optional[str]
    error: Optional[str]

