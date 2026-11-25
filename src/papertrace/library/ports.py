"""A-local PROPOSED_INTEGRATION receipt validation, not a frozen B API."""

import re
from collections.abc import Callable
from typing import Any

Ingest = Callable[[dict[str, Any]], object]
FaultHook = Callable[[str], None]


def ingest_result(ingest: Ingest, request: dict[str, Any]) -> tuple[str, str, str | None]:
    """Treat receipts as untrusted; never expose parser exception text."""
    expected_id = request["document_id"]
    expected_version = request["version_sha256"]
    try:
        receipt = ingest(request)
    except TimeoutError:
        return "failed", "ingest", "INGEST_TIMEOUT"
    except Exception:
        return "failed", "ingest", "INGEST_ERROR"
    invalid = ("failed", "ingest", "INVALID_RECEIPT")
    if not isinstance(receipt, dict):
        return invalid
    if (
        receipt.get("document_id") != expected_id
        or receipt.get("version_sha256") != expected_version
    ):
        return invalid
    status, stage = receipt.get("status"), receipt.get("stage")
    if not isinstance(stage, str) or stage not in {
        "parse", "representation", "ingest", "embedding", "metadata"
    }:
        return invalid
    if status == "ready":
        reference = receipt.get("representation_ref")
        if receipt.get("reason_code") is not None or not isinstance(reference, str):
            return invalid
        if not reference.strip():
            return invalid
        return "ready", stage, None
    reason = receipt.get("reason_code")
    if status != "failed" or not isinstance(reason, str):
        return invalid
    if re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", reason) is None:
        return invalid
    return "failed", stage, reason
