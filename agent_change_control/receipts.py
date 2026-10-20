from __future__ import annotations
import hashlib, hmac, json, os
from datetime import datetime, timezone
from typing import Any


def create_receipt(*, change_id: str, change_hash: str, status: str,
                   validation: dict[str, Any], approver_id: str | None,
                   result: dict[str, Any] | None) -> dict[str, Any]:
    body = {
        "receipt_version": "0.1",
        "change_id": change_id,
        "change_hash": change_hash,
        "status": status,
        "validation": validation,
        "approver_id": approver_id,
        "result": result,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    key = os.environ.get("ACC_RECEIPT_HMAC_KEY", "development-only-key-change-me").encode()
    body["integrity"] = {
        "algorithm": "HMAC-SHA256",
        "signature": hmac.new(key, canonical, hashlib.sha256).hexdigest(),
        "key_configured": key != b"development-only-key-change-me",
    }
    return body
