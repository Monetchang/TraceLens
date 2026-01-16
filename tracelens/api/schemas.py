from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class RunStartRequest(BaseModel):
    name: str
    metadata: Optional[dict] = None


class RunEndRequest(BaseModel):
    status: str = "success"


class RunResponse(BaseModel):
    id: UUID
    name: str
    status: str
    metadata: dict
    started_at: datetime
    ended_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class SpanStartRequest(BaseModel):
    run_id: UUID
    name: str
    parent_span_id: Optional[UUID] = None
    input: Optional[dict] = None
    metadata: Optional[dict] = None


class SpanEndRequest(BaseModel):
    output: Optional[dict] = None


class SpanResponse(BaseModel):
    id: UUID
    run_id: UUID
    name: str
    parent_span_id: Optional[UUID]
    input: dict
    output: dict
    metadata: dict
    started_at: datetime
    ended_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class EventCreateRequest(BaseModel):
    run_id: UUID
    name: str
    data: Optional[dict] = None
    span_id: Optional[UUID] = None


class EventResponse(BaseModel):
    id: UUID
    run_id: UUID
    span_id: Optional[UUID]
    name: str
    data: dict
    created_at: datetime
    
    class Config:
        from_attributes = True


class MetricCreateRequest(BaseModel):
    run_id: UUID
    name: str
    value: Optional[float] = None
    value_json: Optional[dict] = None
    metadata: Optional[dict] = None


class MetricResponse(BaseModel):
    id: UUID
    run_id: UUID
    name: str
    value: Optional[float]
    value_json: Optional[dict]
    metadata: dict
    created_at: datetime
    
    class Config:
        from_attributes = True


class RAGMetricsResponse(BaseModel):
    run_id: UUID
    retrieval_used_ratio: Optional[float]
    unused_chunks_count: int
    context_pollution_rate: Optional[float]
    total_retrieved_chunks: int
    used_chunks: int
    developer_metrics: list[dict]
    chunk_details: list[dict]
    version_info: Optional[dict] = None
    gold_metrics: Optional[dict] = None
    score_stats: Optional[dict] = None

