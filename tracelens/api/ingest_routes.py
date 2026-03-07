import json
from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, RootModel, model_validator
from tracelens.storage.database import get_db
from tracelens.api.dependencies import verify_api_key
from tracelens.ingestion.langsmith import parse_langsmith_run
from tracelens.ingestion.langfuse import parse_langfuse_trace

router = APIRouter(prefix="/api/v1/ingest")

MAX_INGEST_DEPTH = 20
MAX_INGEST_BYTES = 1_000_000


def _check_depth(obj: Any, depth: int = 0) -> None:
    if depth > MAX_INGEST_DEPTH:
        raise ValueError(f"Max nesting depth {MAX_INGEST_DEPTH} exceeded")
    if isinstance(obj, dict):
        for v in obj.values():
            _check_depth(v, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            _check_depth(v, depth + 1)


class IngestPayload(RootModel[dict]):
    """Flexible ingest payload with depth and size limits."""

    @model_validator(mode="after")
    def validate_payload(self) -> "IngestPayload":
        d = self.root
        raw = json.dumps(d)
        if len(raw) > MAX_INGEST_BYTES:
            raise ValueError(f"Payload exceeds max size {MAX_INGEST_BYTES} bytes")
        _check_depth(d)
        return self


class IngestResponse(BaseModel):
    run_id: UUID


@router.post("/langsmith", response_model=IngestResponse)
def ingest_langsmith(data: IngestPayload, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    run_id = parse_langsmith_run(data.model_dump(), db)
    return IngestResponse(run_id=run_id)


@router.post("/langfuse", response_model=IngestResponse)
def ingest_langfuse(data: IngestPayload, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    run_id = parse_langfuse_trace(data.model_dump(), db)
    return IngestResponse(run_id=run_id)

