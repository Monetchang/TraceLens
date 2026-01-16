from uuid import UUID
from typing import Optional, Dict
from sqlalchemy.orm import Session
from tracelens.storage.repository import RunRepository, MetricRepository
from tracelens.storage.rag_repository import RetrievedChunkRepository, PromptChunkRepository, GoldChunkRepository
from tracelens.similarity import get_similarity_engine, SimilarityEngine


def compute_new_chunks_ratio(run_id: UUID, prev_run_id: UUID, db: Session) -> float:
    """计算 new_chunks_ratio"""
    repo = RetrievedChunkRepository(db)
    current = {c.chunk_id for c in repo.get_by_run(run_id)}
    prev = {c.chunk_id for c in repo.get_by_run(prev_run_id)}
    new_count = len(current - prev)
    return new_count / len(current) if current else 0.0


def compute_rank_deltas(run_id: UUID, prev_run_id: UUID, db: Session) -> Dict[str, int]:
    """计算 rank_deltas"""
    repo = RetrievedChunkRepository(db)
    current = repo.get_by_run(run_id)
    prev = repo.get_by_run(prev_run_id)
    
    current_ranks = {c.chunk_id: rank for rank, c in enumerate(current, 1)}
    prev_ranks = {c.chunk_id: rank for rank, c in enumerate(prev, 1)}
    
    rank_deltas = {}
    for chunk_id in set(current_ranks.keys()) & set(prev_ranks.keys()):
        rank_deltas[chunk_id] = current_ranks[chunk_id] - prev_ranks[chunk_id]
    
    return rank_deltas


def compute_all_metrics(
    run_id: UUID,
    db: Session,
    prev_run_id: Optional[UUID] = None,
    similarity_mode: str = "lexical",
    similarity_config: Optional[Dict] = None
) -> Dict:
    """
    计算所有指标
    
    Args:
        run_id: Run ID
        db: Database session
        prev_run_id: 上一版本 Run ID（用于版本对比）
        similarity_mode: 相似度计算模式，可选值：lexical, embedding, llm
        similarity_config: 相似度引擎配置
    """
    metrics = {}
    
    # 如果提供了 prev_run_id，计算版本对比指标
    if prev_run_id:
        metrics["new_chunks_ratio"] = compute_new_chunks_ratio(run_id, prev_run_id, db)
        rank_deltas = compute_rank_deltas(run_id, prev_run_id, db)
        metrics["rank_deltas"] = rank_deltas  # 保留为 dict
    
    # 扩展指标（使用 similarity engine）
    if similarity_mode:
        from tracelens.core.rag_metrics_extended import (
            compute_topk_query_similarity,
            compute_prompt_chunk_answer_similarity,
            compute_semantic_recall_vs_gold,
            compute_new_chunks_query_similarity,
            compute_dropped_chunks_query_similarity
        )
        
        # 创建 similarity engine
        try:
            similarity_engine = get_similarity_engine(similarity_mode, similarity_config)
        except Exception as e:
            print(f"Warning: Failed to create similarity engine: {e}")
            similarity_engine = get_similarity_engine("lexical")  # 回退到默认
        
        # topK_chunk_query_similarity
        topk_sim = compute_topk_query_similarity(run_id, K=5, db=db, similarity_engine=similarity_engine)
        if topk_sim is not None:
            metrics["topK_chunk_query_similarity"] = topk_sim
        
        # prompt_chunk_answer_similarity
        prompt_answer_sim = compute_prompt_chunk_answer_similarity(run_id, db=db, similarity_engine=similarity_engine)
        if prompt_answer_sim is not None:
            metrics["prompt_chunk_answer_similarity"] = prompt_answer_sim
        
        # semantic_recall_vs_gold（可选）
        semantic_recall = compute_semantic_recall_vs_gold(run_id, threshold=0.8, db=db)
        if semantic_recall is not None:
            metrics["semantic_recall_vs_gold"] = semantic_recall
        
        # 版本对比的语义相似度指标
        if prev_run_id:
            new_chunks_sim = compute_new_chunks_query_similarity(run_id, prev_run_id, db=db, similarity_engine=similarity_engine)
            if new_chunks_sim is not None:
                metrics["new_chunks_query_similarity"] = new_chunks_sim
            
            dropped_chunks_sim = compute_dropped_chunks_query_similarity(run_id, prev_run_id, db=db, similarity_engine=similarity_engine)
            if dropped_chunks_sim is not None:
                metrics["dropped_chunks_query_similarity"] = dropped_chunks_sim
    
    # 保存到 metrics 表（只保存数值型指标）
    # 同时保存 similarity_mode
    metric_repo = MetricRepository(db)
    for name, value in metrics.items():
        if name != "rank_deltas" and isinstance(value, (int, float)):
            metric_repo.create(
                run_id,
                name,
                value=float(value),
                metadata={"similarity_mode": similarity_mode}
            )
    
    return metrics
