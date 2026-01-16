from uuid import UUID
from typing import Optional, List, Dict, Set
from dataclasses import dataclass
from sqlalchemy.orm import Session
from tracelens.storage.repository import EventRepository, SpanRepository, RunRepository


@dataclass
class RetrievedChunk:
    chunk_id: str
    score: float
    rank: int
    content: Optional[str] = None


@dataclass
class RetrievalVersion:
    splitter_version: Optional[str] = None
    embedding_model: Optional[str] = None
    vector_db: Optional[str] = None
    index_version: Optional[str] = None


def extract_retrieval_results(run_id: UUID, db: Session) -> List[RetrievedChunk]:
    """从 events 和 spans 提取检索结果，按 rank 排序"""
    event_repo = EventRepository(db)
    span_repo = SpanRepository(db)
    
    chunks_map: Dict[str, RetrievedChunk] = {}
    
    # 从 retrieval span output 提取（优先）
    spans = span_repo.get_by_run(run_id)
    for span in spans:
        if span.name == "retrieval" and span.output:
            chunks = span.output.get("chunks", [])
            for rank, chunk in enumerate(chunks, 1):
                chunk_id = chunk.get("chunk_id") or chunk.get("id")
                if chunk_id:
                    chunks_map[chunk_id] = RetrievedChunk(
                        chunk_id=chunk_id,
                        score=chunk.get("score", 0.0),
                        rank=rank,
                        content=chunk.get("content")
                    )
    
    # 从 chunk_retrieved events 补充（如果没有 span output）
    if not chunks_map:
        events = event_repo.get_by_run(run_id)
        retrieval_events = [e for e in events if e.name == "chunk_retrieved"]
        for rank, event in enumerate(sorted(retrieval_events, key=lambda e: e.data.get("score", 0), reverse=True), 1):
            chunk_id = event.data.get("chunk_id")
            if chunk_id and chunk_id not in chunks_map:
                chunks_map[chunk_id] = RetrievedChunk(
                    chunk_id=chunk_id,
                    score=event.data.get("score", 0.0),
                    rank=rank,
                    content=event.data.get("content")
                )
    
    return sorted(chunks_map.values(), key=lambda c: c.rank)


def extract_version_info(run_id: UUID, db: Session) -> RetrievalVersion:
    """从 run metadata 提取版本信息"""
    run_repo = RunRepository(db)
    run = run_repo.get(run_id)
    if not run or not run.metadata_:
        return RetrievalVersion()
    
    meta = run.metadata_
    return RetrievalVersion(
        splitter_version=meta.get("splitter_version"),
        embedding_model=meta.get("embedding_model"),
        vector_db=meta.get("vector_db"),
        index_version=meta.get("index_version")
    )


def extract_gold_chunks(run_id: UUID, db: Session) -> Set[str]:
    """从 events 或 metadata 提取 gold chunks"""
    event_repo = EventRepository(db)
    run_repo = RunRepository(db)
    
    gold_chunks: Set[str] = set()
    
    # 从 events 提取
    events = event_repo.get_by_run(run_id)
    for event in events:
        if event.name == "gold_chunk":
            chunk_id = event.data.get("chunk_id")
            if chunk_id:
                gold_chunks.add(chunk_id)
    
    # 从 run metadata 提取
    run = run_repo.get(run_id)
    if run and run.metadata_:
        gold = run.metadata_.get("gold_chunks", [])
        gold_chunks.update(gold)
    
    return gold_chunks


def compute_recall_at_k(retrieved: List[RetrievedChunk], gold: Set[str], k: int) -> Optional[float]:
    """计算 Recall@K"""
    if not gold:
        return None
    top_k = retrieved[:k]
    retrieved_ids = {c.chunk_id for c in top_k}
    intersection = retrieved_ids & gold
    return len(intersection) / len(gold) if gold else 0.0


def compute_mrr(retrieved: List[RetrievedChunk], gold: Set[str]) -> Optional[float]:
    """计算 Mean Reciprocal Rank"""
    if not gold:
        return None
    for i, chunk in enumerate(retrieved, 1):
        if chunk.chunk_id in gold:
            return 1.0 / i
    return 0.0


def compute_ndcg_at_k(retrieved: List[RetrievedChunk], gold: Set[str], k: int) -> Optional[float]:
    """计算 nDCG@K（简化版，假设 relevance=1 if in gold else 0）"""
    if not gold:
        return None
    top_k = retrieved[:k]
    dcg = 0.0
    for i, chunk in enumerate(top_k, 1):
        if chunk.chunk_id in gold:
            dcg += 1.0 / (1.0 + i)  # 简化：rel=1
    # 理想 DCG（所有 gold 都在前 k）
    idcg = min(len(gold), k) * (1.0 / 2.0)  # 简化计算
    return dcg / idcg if idcg > 0 else 0.0


def compute_retrieval_diff(retrieved_a: List[RetrievedChunk], retrieved_b: List[RetrievedChunk]) -> Dict:
    """计算两个检索结果的差异"""
    ids_a = {c.chunk_id for c in retrieved_a}
    ids_b = {c.chunk_id for c in retrieved_b}
    
    rank_map_a = {c.chunk_id: c.rank for c in retrieved_a}
    rank_map_b = {c.chunk_id: c.rank for c in retrieved_b}
    
    only_in_a = ids_a - ids_b
    only_in_b = ids_b - ids_a
    in_both = ids_a & ids_b
    
    rank_deltas = {}
    for chunk_id in in_both:
        rank_a = rank_map_a[chunk_id]
        rank_b = rank_map_b[chunk_id]
        rank_deltas[chunk_id] = rank_b - rank_a
    
    return {
        "only_in_a": list(only_in_a),
        "only_in_b": list(only_in_b),
        "in_both": list(in_both),
        "rank_deltas": rank_deltas,
        "total_a": len(retrieved_a),
        "total_b": len(retrieved_b)
    }

