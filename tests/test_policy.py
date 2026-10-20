from agent_change_control.models import ChangePlan
from agent_change_control.policy import evaluate


def plan(sql, env="development", key="idempotency-key-0001"):
    return ChangePlan(agent_id="agent-a", database_id="postgres-dev", environment=env,
                      sql=sql, idempotency_key=key)


def test_simple_select_allowed_without_approval():
    result = evaluate(plan("SELECT id FROM users"))
    assert result.allowed and not result.requires_approval


def test_production_write_requires_approval():
    result = evaluate(plan("UPDATE users SET active = false WHERE id = 1", "production"))
    assert result.allowed and result.requires_approval


def test_drop_requires_approval_and_is_critical():
    result = evaluate(plan("DROP TABLE customers", "production"))
    assert result.allowed and result.requires_approval and result.risk_level == "critical"
    assert "destructive_change_requires_manual_review" in result.reasons


def test_delete_from_is_classified_as_critical_and_requires_approval():
    result = evaluate(plan("DELETE FROM customers WHERE last_seen_at < NOW()", "production"))
    assert result.allowed and result.requires_approval and result.risk_level == "critical"
    assert "destructive_change_requires_manual_review" in result.reasons


def test_multiple_statements_blocked():
    result = evaluate(plan("SELECT 1; DROP TABLE customers"))
    assert not result.allowed


def test_privilege_changes_blocked_even_if_approval_could_be_given():
    result = evaluate(plan("GRANT ALL ON ALL TABLES IN SCHEMA public TO agent"))
    assert not result.allowed


def test_hash_changes_with_payload():
    a = evaluate(plan("SELECT 1"))
    b = evaluate(plan("SELECT 2"))
    assert a.change_hash != b.change_hash
