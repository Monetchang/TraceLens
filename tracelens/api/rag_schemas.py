from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel


class RetrievalCompletedRequest(BaseModel):
    run_id: UUID
    query: Optional[str] = None
    retrieved_chunks: List[dict]  # [{chunk_id, content, score}]


class PromptBuiltRequest(BaseModel):
    run_id: UUID
    prompt_chunks: List[str]  # [chunk_id]


class AnswerGeneratedRequest(BaseModel):
    run_id: UUID
    answer: str


class GoldChunksRequest(BaseModel):
    run_id: UUID
    gold_chunk_ids: List[str]  # [chunk_id]


class RunFinishedRequest(BaseModel):
    run_id: UUID
    status: str = "success"


class ExtendedMetricValue(BaseModel):
    """扩展指标值，含 reliability 和 note"""
    value: float
    reliability: str  # low, medium, high
    note: str


class MetricsResponse(BaseModel):
    run_id: UUID
    metrics: dict  # 基础指标: new_chunks_ratio
    extended_metrics: Optional[dict] = None  # 扩展指标: {name: ExtendedMetricValue} 或 {name: float} 兼容
    gold_available: bool = False
    evaluation_note: Optional[str] = None


class RetrievalDiffResponse(BaseModel):
    run_id: UUID
    prev_run_id: UUID
    new_chunks_ratio: float
    rank_deltas: dict  # chunk_id -> rank_delta
    new_chunks_query_similarity: Optional[float] = None  # 需要 embedding
    dropped_chunks_query_similarity: Optional[float] = None  # 需要 embedding
