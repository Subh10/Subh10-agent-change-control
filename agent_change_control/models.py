from __future__ import annotations
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChangeStatus(StrEnum):
    PLANNED = "planned"
    VALIDATED = "validated"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"
    FAILED = "failed"


class ChangePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: str = Field(min_length=1, max_length=128)
    database_id: str = Field(min_length=1, max_length=128)
    environment: str = Field(min_length=1, max_length=32)
    sql: str = Field(min_length=1, max_length=100_000)
    idempotency_key: str = Field(min_length=8, max_length=256)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    allowed: bool
    requires_approval: bool
    risk_level: str
    reasons: list[str]
    change_hash: str


class ApprovalRequest(BaseModel):
    approver_id: str = Field(min_length=1, max_length=128)
    approved_change_hash: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=3, max_length=1000)


class ChangeRecord(BaseModel):
    id: str
    plan: ChangePlan
    change_hash: str
    status: ChangeStatus
    validation: ValidationResult | None = None
    approver_id: str | None = None
    approval_reason: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    result: dict[str, Any] | None = None
    receipt: dict[str, Any] | None = None
