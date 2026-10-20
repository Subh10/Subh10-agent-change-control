# Agent Change Control (ACC)

Production safety interlock for AI-generated database changes. This is an early, simulation-only prototype; do not use it as a production security boundary.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
python scripts/demo.py
```

## Prototype scope

- Risk checks for proposed SQL changes
- Approval bound to the exact change hash
- Simulation-only execution and signed demo receipts
- FastAPI endpoints and JSON schemas

Policy checks are lexical, state is in-memory, and execution is simulated. A production implementation needs a real SQL parser, database-specific analysis, durable state, secure key management, independent authorization enforcement, and extensive security testing.

Licensed under Apache-2.0. See `LICENSE`.
