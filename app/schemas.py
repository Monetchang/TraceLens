from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class RunCreate(BaseModel):
    app_id: str
    query: str
    index_version: str


class RunResponse(BaseModel):
    run_id: UUID


class ChunkInput(BaseModel):
    chunk_id: UUID
    doc_id: str
    content: str
    score: float
    rank: int


class RetrievalCreate(BaseModel):
    run_id: UUID
    retriever_name: str
    top_k: int
    chunks: list[ChunkInput]


class RetrievalResponse(BaseModel):
    retrieval_id: UUID


class PromptChunkInput(BaseModel):
    chunk_id: UUID
    order_index: int


class PromptChunksCreate(BaseModel):
    run_id: UUID
    chunks: list[PromptChunkInput]


class AnswerCreate(BaseModel):
    run_id: UUID
    answer_text: str


class ChunkAttributionOut(BaseModel):
    chunk_id: UUID
    overlap_tokens: int
    overlap_ratio: float
    used: bool


class RAGMetrics(BaseModel):
    run_id: UUID
    total_answer_tokens: int
    retrieved_chunks: int
    prompt_chunks: int
    used_chunks: int
    retrieval_utilization: float
    pollution_rate: float
    attributions: list[ChunkAttributionOut]


class ChunkDiff(BaseModel):
    chunk_id: UUID
    doc_id: str
    run_a_overlap_ratio: Optional[float]
    run_b_overlap_ratio: Optional[float]
    delta: float


class DiffResponse(BaseModel):
    query: str
    run_a: UUID
    run_b: UUID
    index_version_a: str
    index_version_b: str
    diffs: list[ChunkDiff]

