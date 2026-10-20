"""Conservative prototype policy checks; not a full SQL parser or security boundary."""
from __future__ import annotations
import hashlib
import json
import re
from .models import ChangePlan, ValidationResult

# The MVP intentionally rejects multiple statements and high-risk SQL keywords.
# Production implementation must replace lexical checks with a dialect-aware parser.
MULTI_STATEMENT = re.compile(r";\s*\S")
DESTRUCTIVE = re.compile(r"\b(DELETE\s+FROM|DROP|TRUNCATE|ALTER\s+TABLE\s+\S+\s+DROP)\b", re.I)
DANGEROUS_PRIVILEGE = re.compile(r"\b(GRANT|REVOKE|CREATE\s+ROLE|ALTER\s+ROLE)\b", re.I)
WRITE = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|ALTER|CREATE|DROP|TRUNCATE)\b", re.I)
PROD_NAMES = {"prod", "production", "live"}


def canonical_hash(plan: ChangePlan) -> str:
    payload = plan.model_dump(mode="json", exclude={"metadata"})
    # Metadata is intentionally included in the hash too: it may carry change context.
    payload["metadata"] = plan.metadata
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def evaluate(plan: ChangePlan) -> ValidationResult:
    sql = plan.sql.strip()
    reasons: list[str] = []
    risk = "low"
    requires_approval = False

    if not sql:
        reasons.append("empty_sql")
    if MULTI_STATEMENT.search(sql.rstrip(";")):
        reasons.append("multiple_statements_not_supported")
        risk = "high"
    if DANGEROUS_PRIVILEGE.search(sql):
        reasons.append("privilege_change_not_supported_in_mvp")
        risk = "critical"
    if DESTRUCTIVE.search(sql):
        reasons.append("destructive_change_requires_manual_review")
        risk = "critical"
        requires_approval = True
    elif WRITE.search(sql):
        risk = "medium"
        requires_approval = plan.environment.lower() in PROD_NAMES
    if plan.environment.lower() in PROD_NAMES:
        requires_approval = True
        reasons.append("production_changes_require_approval")
    if "-- acc: allow-destructive" in sql.lower():
        # Explicit comments must never bypass policy.
        reasons.append("inline_policy_overrides_are_ignored")

    # MVP fail-closed: reject unsupported/high-risk patterns; approval is not enough
    # to authorize role/privilege changes or multiple statements.
    blocked = any(x in reasons for x in (
        "multiple_statements_not_supported",
        "privilege_change_not_supported_in_mvp",
    ))
    return ValidationResult(
        allowed=not blocked,
        requires_approval=requires_approval,
        risk_level=risk,
        reasons=reasons or ["no_known_mvp_policy_violation"],
        change_hash=canonical_hash(plan),
    )
