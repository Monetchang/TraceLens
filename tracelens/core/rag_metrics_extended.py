"""
RAG 扩展指标计算（使用 Similarity Engine）
"""
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from tracelens.storage.repository import RunRepository
from tracelens.storage.rag_repository import RetrievedChunkRepository, PromptChunkRepository, GoldChunkRepository
from tracelens.similarity import get_similarity_engine, SimilarityEngine


def compute_topk_query_similarity(
    run_id: UUID,
    K: int,
    db: Session,
    similarity_engine: Optional[SimilarityEngine] = None
) -> Optional[float]:
    """
    计算 topK prompt chunks 与 query 的相似度
    
    Args:
        run_id: Run ID
        K: Top K chunks
        db: Database session
        similarity_engine: 相似度引擎，默认使用 lexical
    """
    run_repo = RunRepository(db)
    run = run_repo.get(run_id)
    if not run or not run.query:
        return None
    
    prompt_repo = PromptChunkRepository(db)
    prompt_chunks = prompt_repo.get_by_run(run_id)
    
    if len(prompt_chunks) == 0:
        return None
    
    # 从 retrieved_chunks 获取 content
    retrieved_repo = RetrievedChunkRepository(db)
    retrieved = {c.chunk_id: c for c in retrieved_repo.get_by_run(run_id)}
    
    # 获取 similarity engine
    if similarity_engine is None:
        similarity_engine = get_similarity_engine("lexical")
    
    try:
        top_k_chunks = prompt_chunks[:K]
        
        similarities = []
        for pc in top_k_chunks:
            chunk = retrieved.get(pc.chunk_id)
            if chunk and chunk.content:
                sim = similarity_engine.compute(run.query, chunk.content)
                similarities.append(sim)
        
        if len(similarities) == 0:
            return None
        
        return sum(similarities) / len(similarities)
    except Exception as e:
        print(f"Warning: Failed to compute topK_query_similarity: {e}")
        return None


def compute_prompt_chunk_answer_similarity(
    run_id: UUID,
    db: Session,
    similarity_engine: Optional[SimilarityEngine] = None
) -> Optional[float]:
    """
    计算 prompt chunks 与 answer 的相似度
    
    Args:
        run_id: Run ID
        db: Database session
        similarity_engine: 相似度引擎，默认使用 lexical
    """
    run_repo = RunRepository(db)
    run = run_repo.get(run_id)
    if not run or not run.answer:
        return None
    
    prompt_repo = PromptChunkRepository(db)
    prompt_chunks = prompt_repo.get_by_run(run_id)
    
    if len(prompt_chunks) == 0:
        return None
    
    # 从 retrieved_chunks 获取 content
    retrieved_repo = RetrievedChunkRepository(db)
    retrieved = {c.chunk_id: c for c in retrieved_repo.get_by_run(run_id)}
    
    # 获取 similarity engine
    if similarity_engine is None:
        similarity_engine = get_similarity_engine("lexical")
    
    try:
        similarities = []
        for pc in prompt_chunks:
            chunk = retrieved.get(pc.chunk_id)
            if chunk and chunk.content:
                sim = similarity_engine.compute(
                    chunk.content,
                    run.answer,
                    context={"type": "chunk_answer"}
                )
                similarities.append(sim)
        
        if len(similarities) == 0:
            return None
        
        return sum(similarities) / len(similarities)
    except Exception as e:
        print(f"Warning: Failed to compute prompt_chunk_answer_similarity: {e}")
        return None


def compute_semantic_recall_vs_gold(
    run_id: UUID,
    threshold: float = 0.8,
    db: Session = None
) -> Optional[float]:
    """
    计算相对于 gold chunks 的语义召回率
    
    简化版本：只检查 chunk_id 是否匹配
    """
    chunk_repo = RetrievedChunkRepository(db)
    gold_repo = GoldChunkRepository(db)
    
    retrieved = chunk_repo.get_by_run(run_id)
    gold_chunks = gold_repo.get_by_run(run_id)
    
    if len(gold_chunks) == 0:
        return None
    
    # 简化版本：只检查 chunk_id 是否在 retrieved 中
    retrieved_chunk_ids = {chunk.chunk_id for chunk in retrieved}
    gold_chunk_ids = {gold.chunk_id for gold in gold_chunks}
    
    hit_count = len(retrieved_chunk_ids & gold_chunk_ids)
    return hit_count / len(gold_chunk_ids) if len(gold_chunk_ids) > 0 else 0.0


def compute_new_chunks_query_similarity(
    run_id: UUID,
    prev_run_id: UUID,
    db: Session,
    similarity_engine: Optional[SimilarityEngine] = None
) -> Optional[float]:
    """
    计算新增 chunks 与 query 的相似度
    
    Args:
        run_id: Run ID
        prev_run_id: 上一版本 Run ID
        db: Database session
        similarity_engine: 相似度引擎，默认使用 lexical
    """
    run_repo = RunRepository(db)
    run = run_repo.get(run_id)
    if not run or not run.query:
        return None
    
    chunk_repo = RetrievedChunkRepository(db)
    current = chunk_repo.get_by_run(run_id)
    prev = chunk_repo.get_by_run(prev_run_id)
    
    current_ids = {c.chunk_id for c in current}
    prev_ids = {c.chunk_id for c in prev}
    
    new_chunk_ids = current_ids - prev_ids
    new_chunks = [c for c in current if c.chunk_id in new_chunk_ids]
    
    if len(new_chunks) == 0:
        return 0.0
    
    # 获取 similarity engine
    if similarity_engine is None:
        similarity_engine = get_similarity_engine("lexical")
    
    try:
        similarities = []
        for chunk in new_chunks:
            if chunk.content:
                sim = similarity_engine.compute(run.query, chunk.content)
                similarities.append(sim)
        
        if len(similarities) == 0:
            return None
        
        return sum(similarities) / len(similarities)
    except Exception as e:
        print(f"Warning: Failed to compute new_chunks_query_similarity: {e}")
        return None


def compute_dropped_chunks_query_similarity(
    run_id: UUID,
    prev_run_id: UUID,
    db: Session,
    similarity_engine: Optional[SimilarityEngine] = None
) -> Optional[float]:
    """
    计算丢弃 chunks 与 query 的相似度
    
    Args:
        run_id: Run ID
        prev_run_id: 上一版本 Run ID
        db: Database session
        similarity_engine: 相似度引擎，默认使用 lexical
    """
    run_repo = RunRepository(db)
    run = run_repo.get(run_id)
    if not run or not run.query:
        return None
    
    chunk_repo = RetrievedChunkRepository(db)
    current = chunk_repo.get_by_run(run_id)
    prev = chunk_repo.get_by_run(prev_run_id)
    
    current_ids = {c.chunk_id for c in current}
    prev_ids = {c.chunk_id for c in prev}
    
    dropped_chunk_ids = prev_ids - current_ids
    dropped_chunks = [c for c in prev if c.chunk_id in dropped_chunk_ids]
    
    if len(dropped_chunks) == 0:
        return 0.0
    
    # 获取 similarity engine
    if similarity_engine is None:
        similarity_engine = get_similarity_engine("lexical")
    
    try:
        similarities = []
        for chunk in dropped_chunks:
            if chunk.content:
                sim = similarity_engine.compute(run.query, chunk.content)
                similarities.append(sim)
        
        if len(similarities) == 0:
            return None
        
        return sum(similarities) / len(similarities)
    except Exception as e:
        print(f"Warning: Failed to compute dropped_chunks_query_similarity: {e}")
        return None
