"""Run a deterministic, local-only walkthrough of the ACC safety gate.

No network calls and no database connections are made by this script.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from textwrap import indent

# Allow `python scripts/demo.py` from a fresh repository checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_change_control.models import ApprovalRequest, ChangePlan
from agent_change_control.service import (
    ChangeService,
    ConflictError,
    UnsafeExecutionError,
)


def line(char: str = "─", width: int = 72) -> None:
    print(char * width)


def section(number: int, title: str) -> None:
    print()
    line("═")
    print(f"  {number}. {title}")
    line("═")


def show_json(value: object) -> None:
    print(indent(json.dumps(value, indent=2, sort_keys=True), "    "))


def main() -> int:
    service = ChangeService()
    plan = ChangePlan(
        agent_id="demo-coding-agent",
        database_id="customer-prod-postgres",
        environment="production",
        sql="DELETE FROM customers WHERE last_seen_at < NOW() - INTERVAL '3 years'",
        idempotency_key="demo-customer-cleanup-v01",
        metadata={"ticket": "DEMO-1042", "purpose": "customer data retention cleanup"},
    )

    print("\nAGENT CHANGE CONTROL — LOCAL WALKTHROUGH")
    print("A local simulation. No database is contacted; no SQL is executed.")

    section(1, "An AI agent proposes a production change")
    print(f"    Agent:       {plan.agent_id}")
    print(f"    Database:    {plan.database_id}")
    print(f"    Environment: {plan.environment}")
    print(f"    SQL:         {plan.sql}")
    record = service.plan(plan)
    print(f"\n    ACC change ID: {record.id}")
    print(f"    SHA-256:      {record.change_hash}")

    section(2, "Policy evaluation flags the production write")
    record = service.validate(record.id)
    assert record.validation is not None
    print(f"    Status:       {record.status.value.upper()}")
    print(f"    Risk:         {record.validation.risk_level.upper()}")
    print(f"    Allowed:      {record.validation.allowed}")
    print(f"    Approval:     {'REQUIRED' if record.validation.requires_approval else 'not required'}")
    print("    Reasons:")
    for reason in record.validation.reasons:
        print(f"      • {reason}")

    section(3, "Execution is denied before approval")
    try:
        service.execute_simulated(record.id)
        print("    ERROR: execution unexpectedly passed the approval gate")
        return 1
    except UnsafeExecutionError as exc:
        print(f"    DENIED: {exc}")

    section(4, "Approval must reference the exact change hash")
    try:
        service.approve(
            record.id,
            ApprovalRequest(
                approver_id="demo-human-reviewer",
                approved_change_hash="0" * 64,
                reason="This is intentionally the wrong hash for the demo.",
            ),
        )
        print("    ERROR: mismatched approval unexpectedly passed")
        return 1
    except ConflictError as exc:
        print(f"    MISMATCH REJECTED: {exc}")

    record = service.approve(
        record.id,
        ApprovalRequest(
            approver_id="demo-human-reviewer",
            approved_change_hash=record.change_hash,
            reason="Reviewed the intended retention cleanup for this demo.",
        ),
    )
    print(f"    APPROVED by: {record.approver_id}")
    print(f"    Bound hash:  {record.change_hash}")

    section(5, "Simulated execution emits an evidence receipt")
    record = service.execute_simulated(record.id)
    print(f"    Status: {record.status.value.upper()}")
    print(f"    Result: {record.result['message'] if record.result else 'missing'}")
    receipt = record.receipt
    if not receipt:
        print("    ERROR: receipt was not generated")
        return 1
    print("    Receipt summary:")
    show_json({
        "change_id": receipt.get("change_id"),
        "change_hash": receipt.get("change_hash"),
        "status": receipt.get("status"),
        "approver_id": receipt.get("approver_id"),
        "integrity": receipt.get("integrity"),
    })

    section(6, "A separate unsupported multi-statement proposal is blocked")
    blocked_plan = ChangePlan(
        agent_id="demo-coding-agent",
        database_id="customer-prod-postgres",
        environment="production",
        sql="UPDATE customers SET active = false; DROP TABLE customers",
        idempotency_key="demo-multi-statement-v01",
    )
    blocked = service.plan(blocked_plan)
    blocked = service.validate(blocked.id)
    print(f"    Status:  {blocked.status.value.upper()}")
    print(f"    Allowed: {blocked.validation.allowed if blocked.validation else False}")
    if blocked.validation:
        for reason in blocked.validation.reasons:
            print(f"      • {reason}")
    try:
        service.execute_simulated(blocked.id)
        print("    ERROR: blocked proposal unexpectedly passed")
        return 1
    except (UnsafeExecutionError, ConflictError) as exc:
        print(f"    EXECUTION DENIED: {exc}")

    print()
    line("═")
    print("  DEMO COMPLETE — all database execution was simulated.")
    print("  Prototype only: lexical policy checks are not a SQL parser or security boundary.")
    line("═")
    return 0


if __name__ == "__main__":
    sys.exit(main())
