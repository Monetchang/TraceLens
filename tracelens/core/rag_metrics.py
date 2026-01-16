from uuid import UUID
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from tracelens.storage.repository import EventRepository, MetricRepository, RunRepository
from tracelens.core.retrieval_analysis import (
    extract_retrieval_results, extract_version_info, extract_gold_chunks,
    compute_recall_at_k, compute_mrr, compute_ndcg_at_k
)
from tracelens.api.schemas import RAGMetricsResponse


def compute_rag_metrics(run_id: UUID, db: Session) -> RAGMetricsResponse:
    """计算 RAG metrics（支持 gold-aware 和 gold-optional）"""
    event_repo = EventRepository(db)
    metric_repo = MetricRepository(db)
    run_repo = RunRepository(db)
    
    run = run_repo.get(run_id)
    events = event_repo.get_by_run(run_id)
    metrics = metric_repo.get_by_run(run_id)
    
    # 提取检索结果
    retrieved = extract_retrieval_results(run_id, db)
    version = extract_version_info(run_id, db)
    gold_chunks = extract_gold_chunks(run_id, db)
    
    # 提取使用的 chunks
    used_chunk_ids = set()
    for event in events:
        if event.name == "chunk_used":
            chunk_id = event.data.get("chunk_id")
            if chunk_id:
                used_chunk_ids.add(chunk_id)
    
    # 构建 chunk_details
    chunk_details = []
    for chunk in retrieved:
        chunk_details.append({
            "chunk_id": chunk.chunk_id,
            "rank": chunk.rank,
            "score": chunk.score,
            "is_gold": chunk.chunk_id in gold_chunks,
            "used": chunk.chunk_id in used_chunk_ids,
            "content_preview": chunk.content[:100] if chunk.content else None
        })
    
    # Gold-aware metrics（如果有 gold data）
    recall_at_5 = compute_recall_at_k(retrieved, gold_chunks, 5) if gold_chunks else None
    recall_at_10 = compute_recall_at_k(retrieved, gold_chunks, 10) if gold_chunks else None
    mrr = compute_mrr(retrieved, gold_chunks) if gold_chunks else None
    ndcg_at_10 = compute_ndcg_at_k(retrieved, gold_chunks, 10) if gold_chunks else None
    
    # Gold-optional metrics（无 gold 时也可计算）
    total_retrieved = len(retrieved)
    total_used = len(used_chunk_ids)
    unused_count = total_retrieved - total_used
    
    retrieval_used_ratio = total_used / total_retrieved if total_retrieved > 0 else None
    pollution_rate = unused_count / total_retrieved if total_retrieved > 0 else None
    
    # 评分统计（无 gold 时的参考指标）
    score_stats = None
    if retrieved:
        scores = [c.score for c in retrieved]
        score_stats = {
            "mean": sum(scores) / len(scores),
            "max": max(scores),
            "min": min(scores),
            "top_3_mean": sum(scores[:3]) / min(3, len(scores)) if scores else 0.0
        }
    
    developer_metrics = [
        {"name": m.name, "value": m.value, "value_json": m.value_json, "metadata": m.metadata_}
        for m in metrics
    ]
    
    return RAGMetricsResponse(
        run_id=run_id,
        retrieval_used_ratio=retrieval_used_ratio,
        unused_chunks_count=unused_count,
        context_pollution_rate=pollution_rate,
        total_retrieved_chunks=total_retrieved,
        used_chunks=total_used,
        developer_metrics=developer_metrics,
        chunk_details=chunk_details,
        version_info={
            "splitter_version": version.splitter_version,
            "embedding_model": version.embedding_model,
            "vector_db": version.vector_db,
            "index_version": version.index_version
        },
        gold_metrics={
            "recall_at_5": recall_at_5,
            "recall_at_10": recall_at_10,
            "mrr": mrr,
            "ndcg_at_10": ndcg_at_10,
            "has_gold": len(gold_chunks) > 0
        },
        score_stats=score_stats
    )
