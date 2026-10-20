from __future__ import annotations
from threading import RLock
from uuid import uuid4
from .models import ChangePlan, ChangeRecord, ChangeStatus, ApprovalRequest, utcnow
from .policy import evaluate, canonical_hash
from .receipts import create_receipt


class ConflictError(Exception): pass
class NotFoundError(Exception): pass
class UnsafeExecutionError(Exception): pass


class ChangeService:
    """In-memory demo service. Not durable and not suitable for production."""
    def __init__(self):
        self._records: dict[str, ChangeRecord] = {}
        self._idempotency: dict[tuple[str, str], str] = {}
        self._lock = RLock()

    def plan(self, plan: ChangePlan) -> ChangeRecord:
        key = (plan.agent_id, plan.idempotency_key)
        digest = canonical_hash(plan)
        with self._lock:
            prior_id = self._idempotency.get(key)
            if prior_id:
                prior = self._records[prior_id]
                if prior.change_hash != digest:
                    raise ConflictError("idempotency_key_reused_with_different_payload")
                return prior
            record = ChangeRecord(id=f"chg_{uuid4().hex}", plan=plan,
                                  change_hash=digest, status=ChangeStatus.PLANNED)
            self._records[record.id] = record
            self._idempotency[key] = record.id
            return record

    def validate(self, change_id: str) -> ChangeRecord:
        with self._lock:
            rec = self._get(change_id)
            if canonical_hash(rec.plan) != rec.change_hash:
                raise ConflictError("change_payload_hash_mismatch")
            result = evaluate(rec.plan)
            rec.validation = result
            if not result.allowed:
                rec.status = ChangeStatus.BLOCKED
            elif result.requires_approval:
                rec.status = ChangeStatus.APPROVAL_REQUIRED
            else:
                rec.status = ChangeStatus.VALIDATED
            rec.updated_at = utcnow()
            return rec

    def approve(self, change_id: str, approval: ApprovalRequest) -> ChangeRecord:
        with self._lock:
            rec = self._get(change_id)
            if rec.status != ChangeStatus.APPROVAL_REQUIRED:
                raise ConflictError("change_not_waiting_for_approval")
            if not rec.validation or not rec.validation.allowed:
                raise ConflictError("change_not_validated")
            if approval.approved_change_hash != rec.change_hash:
                raise ConflictError("approval_hash_does_not_match_exact_change")
            # Approval never overrides blocked policy checks.
            rec.approver_id = approval.approver_id
            rec.approval_reason = approval.reason
            rec.status = ChangeStatus.APPROVED
            rec.updated_at = utcnow()
            return rec

    def execute_simulated(self, change_id: str) -> ChangeRecord:
        """Simulates execution only. Deliberately does not connect to a database."""
        with self._lock:
            rec = self._get(change_id)
            if not rec.validation or not rec.validation.allowed:
                raise UnsafeExecutionError("change_has_no_valid_allow_decision")
            if rec.status == ChangeStatus.APPROVAL_REQUIRED:
                raise UnsafeExecutionError("approval_required_before_execution")
            if rec.status not in (ChangeStatus.VALIDATED, ChangeStatus.APPROVED):
                if rec.status == ChangeStatus.SUCCEEDED:
                    return rec
                raise ConflictError(f"change_not_executable_from_{rec.status.value}")
            if canonical_hash(rec.plan) != rec.change_hash:
                raise UnsafeExecutionError("approved_payload_changed")
            rec.status = ChangeStatus.SUCCEEDED
            rec.result = {"mode": "simulation", "executed": False,
                          "message": "No SQL was sent to any database."}
            rec.receipt = create_receipt(
                change_id=rec.id, change_hash=rec.change_hash, status=rec.status.value,
                validation=rec.validation.model_dump(mode="json"),
                approver_id=rec.approver_id, result=rec.result,
            )
            rec.updated_at = utcnow()
            return rec

    def get(self, change_id: str) -> ChangeRecord:
        with self._lock:
            return self._get(change_id)

    def _get(self, change_id: str) -> ChangeRecord:
        try: return self._records[change_id]
        except KeyError: raise NotFoundError(change_id) from None
