from fastapi import FastAPI, HTTPException
from .models import ChangePlan, ApprovalRequest, ChangeRecord
from .service import ChangeService, ConflictError, NotFoundError, UnsafeExecutionError

app = FastAPI(title="Agent Change Control API", version="0.1.0",
              description="Prototype policy gate. Execution endpoint is simulation-only.")
service = ChangeService()


def translate(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError): return HTTPException(404, "change_not_found")
    if isinstance(exc, ConflictError): return HTTPException(409, str(exc))
    if isinstance(exc, UnsafeExecutionError): return HTTPException(403, str(exc))
    return HTTPException(400, "request_rejected")


@app.get("/health")
def health(): return {"status": "ok", "mode": "simulation-only"}

@app.post("/v1/changes/plan", response_model=ChangeRecord, status_code=201)
def plan_change(plan: ChangePlan):
    try: return service.plan(plan)
    except Exception as e: raise translate(e)

@app.post("/v1/changes/{change_id}/validate", response_model=ChangeRecord)
def validate_change(change_id: str):
    try: return service.validate(change_id)
    except Exception as e: raise translate(e)

@app.post("/v1/changes/{change_id}/approve", response_model=ChangeRecord)
def approve_change(change_id: str, approval: ApprovalRequest):
    try: return service.approve(change_id, approval)
    except Exception as e: raise translate(e)

@app.post("/v1/changes/{change_id}/execute", response_model=ChangeRecord)
def execute_change(change_id: str):
    try: return service.execute_simulated(change_id)
    except Exception as e: raise translate(e)

@app.get("/v1/changes/{change_id}", response_model=ChangeRecord)
def get_change(change_id: str):
    try: return service.get(change_id)
    except Exception as e: raise translate(e)

@app.get("/v1/changes/{change_id}/receipt")
def get_receipt(change_id: str):
    try:
        rec = service.get(change_id)
        if not rec.receipt: raise HTTPException(409, "receipt_not_available_until_simulated_execution")
        return rec.receipt
    except HTTPException: raise
    except Exception as e: raise translate(e)
