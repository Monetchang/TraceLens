from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from tracelens.storage.database import get_db
from tracelens.ingestion.langsmith import parse_langsmith_run
from tracelens.ingestion.langfuse import parse_langfuse_trace

router = APIRouter(prefix="/api/v1/ingest")


class IngestResponse(BaseModel):
    run_id: UUID


@router.post("/langsmith", response_model=IngestResponse)
def ingest_langsmith(data: dict, db: Session = Depends(get_db)):
    run_id = parse_langsmith_run(data, db)
    return IngestResponse(run_id=run_id)


@router.post("/langfuse", response_model=IngestResponse)
def ingest_langfuse(data: dict, db: Session = Depends(get_db)):
    run_id = parse_langfuse_trace(data, db)
    return IngestResponse(run_id=run_id)

