# Agent Change Control

**A prototype policy gate for AI-proposed database changes.** The first wedge is production database change control for AI coding agents.

> **Safety status: prototype only.** This repository does not connect to a database. The `/execute` endpoint is simulation-only. The policy evaluator uses conservative lexical checks, not a dialect-aware SQL parser. Do not use it to protect production systems.

## Why this wedge

Generic agent permissions are broad. Database changes have a specific and costly failure mode: an agent can produce plausible SQL that deletes data, locks a hot table, or breaks compatibility between old and new application versions. This prototype explores a narrow control point: bind a change proposal to a policy decision, approval and tamper-evident receipt.

## Current vertical slice

- Pydantic change contract with strict input fields
- SHA-256 canonical change hash
- Fail-closed handling for multi-statement and privilege-changing SQL patterns
- Production writes require explicit approval
- Approval is bound to the exact change hash
- Idempotency-key collision detection
- Simulation-only execution endpoint
- HMAC-SHA256 receipt integrity field
- OpenAPI contract and JSON Schemas
- Unit/API tests

## Quickstart

Python 3.11+ recommended.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -e '.[test]'
pytest
uvicorn agent_change_control.api:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API docs.

Evaluate a proposed production change locally:

```bash
acc --environment production --sql "UPDATE users SET active = false WHERE id = 1"
```

## 5-minute safety-gate demo

Run a guided, deterministic walkthrough with no server, network, or database required:

```bash
python scripts/demo.py
```

The demo shows a proposed production data cleanup, policy evaluation, denial before approval, rejection of a mismatched approval hash, successful approval bound to the exact change, a signed simulation receipt, and a separate multi-statement proposal that is blocked. **It never sends SQL to a database.**

For a live API walkthrough instead, start Uvicorn in one terminal and use the interactive docs at `http://127.0.0.1:8000/docs`.

## API flow

1. `POST /v1/changes/plan` with `agent_id`, `database_id`, `environment`, `sql`, and `idempotency_key`.
2. `POST /v1/changes/{id}/validate` to compute a policy result.
3. If approval is required, `POST /v1/changes/{id}/approve` with the exact `approved_change_hash` returned by validation.
4. `POST /v1/changes/{id}/execute` runs a **simulation only** and emits a receipt.
5. `GET /v1/changes/{id}/receipt` retrieves the receipt.

## Receipt signing

Set `ACC_RECEIPT_HMAC_KEY` to a high-entropy secret for non-demo use. The default development key is public and must never be trusted. The prototype signs the receipt body with HMAC-SHA256; it is not a public verifiable signature and does not itself make storage immutable. A production design should use KMS-backed signing, durable append-only event storage, key rotation, and independent receipt verification.

## Non-goals in v0.1

- Real database execution
- Claiming SQL safety from regex checks
- Automatic rollback guarantees
- Production authentication, tenancy or authorization
- Durable state or distributed idempotency
- Immutable storage / third-party timestamping
- Certification or compliance claims

## Security model still to implement

Before any real execution adapter is considered: dialect-aware SQL parsing; strict allow-list of operations; credentials held only by the execution service; separate read-only validation and constrained execution roles; transaction and lock-time limits; policy versioning; expiring approvals; database-native advisory locks; durable idempotency; post-execution state verification; unknown-state reconciliation; recovery drills; tenant isolation; authenticated approver identity; audit retention; adversarial tests; and explicit human-controlled kill switch.

## Repository layout

```text
agent-change-control/
├── agent_change_control/   # API, policy, service, receipts, CLI
├── api/openapi.yaml        # OpenAPI contract
├── spec/                   # JSON Schemas
├── examples/               # Example payload
└── tests/                  # Policy, API and invariant tests
```

## License

Apache-2.0. See `LICENSE`.
