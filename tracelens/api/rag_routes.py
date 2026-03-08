from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from tracelens.storage.database import get_db
from tracelens.api.dependencies import verify_api_key
from tracelens.storage.repository import RunRepository
from tracelens.storage.rag_repository import (
    RetrievedChunkRepository, PromptChunkRepository, GoldChunkRepository
)
from tracelens.core.rag_metrics_simple import compute_all_metrics
from tracelens.api.rag_schemas import (
    RetrievalCompletedRequest, PromptBuiltRequest, AnswerGeneratedRequest,
    GoldChunksRequest, RunFinishedRequest,
    MetricsResponse, RetrievalDiffResponse, ExtendedMetricValue
)

router = APIRouter(prefix="/api/v1")


@router.post("/retrieval/completed")
def retrieval_completed(req: RetrievalCompletedRequest, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """上报 retrieval_completed 事件"""
    run_repo = RunRepository(db)
    run = run_repo.get(req.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if req.query:
        run.query = req.query
        db.commit()
    
    chunk_repo = RetrievedChunkRepository(db)
    chunk_repo.bulk_create(req.run_id, req.retrieved_chunks)
    
    return {"status": "ok"}


@router.post("/prompt/built")
def prompt_built(req: PromptBuiltRequest, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """上报 prompt_built 事件"""
    run_repo = RunRepository(db)
    run = run_repo.get(req.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    prompt_repo = PromptChunkRepository(db)
    prompt_repo.bulk_create(req.run_id, req.prompt_chunks)
    
    return {"status": "ok"}


@router.post("/answer/generated")
def answer_generated(req: AnswerGeneratedRequest, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """上报 answer_generated 事件"""
    run_repo = RunRepository(db)
    run = run_repo.get(req.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run.answer = req.answer
    db.commit()
    
    return {"status": "ok"}


@router.post("/gold/chunks")
def gold_chunks(req: GoldChunksRequest, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """上报 gold_chunks 事件（可选）"""
    run_repo = RunRepository(db)
    run = run_repo.get(req.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    gold_repo = GoldChunkRepository(db)
    gold_repo.bulk_create(req.run_id, req.gold_chunk_ids)
    
    return {"status": "ok"}


@router.post("/run/finished")
def run_finished(req: RunFinishedRequest, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """上报 run_finished 事件"""
    run_repo = RunRepository(db)
    run = run_repo.end(req.run_id, status=req.status)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return {"status": "ok"}


@router.get("/run/{run_id}/metrics", response_model=MetricsResponse)
def get_metrics(
    run_id: UUID,
    prev_run_id: Optional[UUID] = Query(None, description="上一版本的 run_id，用于计算版本对比指标"),
    similarity_mode: str = Query("lexical", description="相似度计算模式：lexical, embedding, llm"),
    db: Session = Depends(get_db)
):
    """获取 run 的所有 metrics"""
    from tracelens.storage.repository import MetricRepository
    
    run_repo = RunRepository(db)
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # 计算并保存 metrics
    metrics = compute_all_metrics(
        run_id,
        db,
        prev_run_id=prev_run_id,
        similarity_mode=similarity_mode
    )
    
    metric_repo = MetricRepository(db)
    db_metrics = metric_repo.get_by_run_and_mode(run_id, similarity_mode)
    metrics_dict = {}
    for m in sorted(db_metrics, key=lambda x: (0 if x.similarity_mode == "" else 1)):
        if m.value is not None:
            metrics_dict[m.name] = m.value
    metrics_dict.update({k: v for k, v in metrics.items() if k != "rank_deltas" and k != "_similarity_mode_used" and isinstance(v, (int, float))})
    effective_mode = metrics.get("_similarity_mode_used", similarity_mode)

    # 分离基础指标和扩展指标
    extended_keys = {
        "topK_chunk_query_similarity",
        "prompt_chunk_answer_similarity",
        "exact_recall_vs_gold_chunks",
        "new_chunks_query_similarity",
        "dropped_chunks_query_similarity",
        "answer_faithfulness"
    }
    base_metrics = {k: v for k, v in metrics_dict.items() if k not in extended_keys}
    raw_extended = {k: v for k, v in metrics_dict.items() if k in extended_keys} if similarity_mode else None

    # 方案1: 为扩展指标注入 reliability 和 note（使用实际生效的 mode，含 LLM 采样降级）
    reliability_map = {
        "lexical": ("low", "基于词面重叠近似，不代表检索关联度"),
        "embedding": ("medium", "语义相似度近似关联度，建议配合 gold_chunks 使用 exact_recall 指标"),
        "llm": ("high", "LLM 直接评估 query-chunk 关联度、chunk-answer 支撑度"),
    }
    rel, note = reliability_map.get(effective_mode, ("low", ""))

    extended_metrics = None
    if raw_extended:
        extended_metrics = {
            k: ExtendedMetricValue(value=v, reliability=rel, note=note)
            for k, v in raw_extended.items()
            if v is not None and isinstance(v, (int, float))
        }

    # 方案2: gold_available 和 evaluation_note
    gold_repo = GoldChunkRepository(db)
    gold_available = len(gold_repo.get_by_run(run_id)) > 0
    evaluation_note = None
    if not gold_available:
        evaluation_note = "未上报 gold_chunks，当前相似度指标仅为参考值。上报 gold_chunks 可获得更可信的 exact_recall 指标。"

    return MetricsResponse(
        run_id=run_id,
        metrics=base_metrics,
        extended_metrics=extended_metrics if extended_metrics else None,
        gold_available=gold_available,
        evaluation_note=evaluation_note
    )


@router.get("/run/{run_id}/retrieval_diff", response_model=RetrievalDiffResponse)
def get_retrieval_diff(
    run_id: UUID,
    prev_run_id: UUID = Query(...),
    similarity_mode: str = Query("lexical", description="相似度计算模式：lexical, embedding, llm"),
    db: Session = Depends(get_db)
):
    """获取 retrieval diff"""
    from tracelens.core.rag_metrics_simple import compute_new_chunks_ratio, compute_rank_deltas
    from tracelens.similarity import get_similarity_engine
    
    run_repo = RunRepository(db)
    run = run_repo.get(run_id)
    prev_run = run_repo.get(prev_run_id)
    if not run or not prev_run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    new_ratio = compute_new_chunks_ratio(run_id, prev_run_id, db)
    rank_deltas = compute_rank_deltas(run_id, prev_run_id, db)
    
    new_chunks_sim = None
    dropped_chunks_sim = None
    
    if similarity_mode:
        from tracelens.core.rag_metrics_extended import (
            compute_new_chunks_query_similarity,
            compute_dropped_chunks_query_similarity
        )
        
        # 创建 similarity engine
        try:
            similarity_engine = get_similarity_engine(similarity_mode)
        except Exception:
            similarity_engine = get_similarity_engine("lexical")  # 回退到默认
        
        new_chunks_sim = compute_new_chunks_query_similarity(run_id, prev_run_id, db, similarity_engine)
        dropped_chunks_sim = compute_dropped_chunks_query_similarity(run_id, prev_run_id, db, similarity_engine)
    
    return RetrievalDiffResponse(
        run_id=run_id,
        prev_run_id=prev_run_id,
        new_chunks_ratio=new_ratio,
        rank_deltas=rank_deltas,
        new_chunks_query_similarity=new_chunks_sim,
        dropped_chunks_query_similarity=dropped_chunks_sim
    )
