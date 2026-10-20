import pytest
from fastapi.testclient import TestClient
from agent_change_control.api import app
from agent_change_control.models import ChangePlan, ApprovalRequest
from agent_change_control.service import ChangeService, ConflictError, UnsafeExecutionError

client = TestClient(app)


def test_idempotency_same_payload_returns_same_change():
    s = ChangeService()
    p = ChangePlan(agent_id="a", database_id="db", environment="development",
                   sql="SELECT 1", idempotency_key="idem-key-0001")
    first = s.plan(p); second = s.plan(p)
    assert first.id == second.id


def test_idempotency_key_reuse_with_different_payload_conflicts():
    s = ChangeService()
    p1 = ChangePlan(agent_id="a", database_id="db", environment="development",
                    sql="SELECT 1", idempotency_key="idem-key-0001")
    p2 = p1.model_copy(update={"sql": "SELECT 2"})
    s.plan(p1)
    with pytest.raises(ConflictError): s.plan(p2)


def test_approval_must_match_exact_hash():
    s = ChangeService()
    p = ChangePlan(agent_id="a", database_id="db", environment="production",
                   sql="UPDATE users SET active = false", idempotency_key="idem-key-0002")
    rec = s.plan(p); rec = s.validate(rec.id)
    with pytest.raises(ConflictError):
        s.approve(rec.id, ApprovalRequest(approver_id="human-1",
                    approved_change_hash="0" * 64, reason="Reviewed migration"))


def test_production_change_cannot_execute_before_approval():
    s = ChangeService()
    p = ChangePlan(agent_id="a", database_id="db", environment="production",
                   sql="UPDATE users SET active = false", idempotency_key="idem-key-0003")
    rec = s.plan(p); rec = s.validate(rec.id)
    with pytest.raises(UnsafeExecutionError): s.execute_simulated(rec.id)


def test_simulated_execution_produces_receipt_and_never_executes_sql():
    s = ChangeService()
    p = ChangePlan(agent_id="a", database_id="db", environment="development",
                   sql="SELECT 1", idempotency_key="idem-key-0004")
    rec = s.plan(p); rec = s.validate(rec.id); rec = s.execute_simulated(rec.id)
    assert rec.receipt["change_hash"] == rec.change_hash
    assert rec.result["executed"] is False
    assert rec.receipt["integrity"]["algorithm"] == "HMAC-SHA256"


def test_http_health_is_simulation_only():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["mode"] == "simulation-only"
