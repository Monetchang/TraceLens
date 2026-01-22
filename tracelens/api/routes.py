from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from tracelens.storage.database import get_db
from tracelens.storage.repository import RunRepository, SpanRepository, EventRepository, MetricRepository
from tracelens.storage.evaluation_repository import TestCaseRepository, EvaluationRepository
from tracelens.storage.rag_repository import GoldChunkRepository
from tracelens.api.schemas import (
    RunStartRequest, RunEndRequest, RunResponse,
    SpanStartRequest, SpanEndRequest, SpanResponse,
    EventCreateRequest, EventResponse,
    MetricCreateRequest, MetricResponse,
    RAGMetricsResponse
)
from tracelens.core.rag_metrics import compute_rag_metrics
from tracelens.core.run_graph import build_run_graph
from tracelens.core.chunk_attribution import compute_chunk_attribution
from tracelens.core.retrieval_analysis import (
    extract_retrieval_results, extract_version_info, compute_retrieval_diff
)

router = APIRouter(prefix="/api/v1")


@router.post("/run/start", response_model=RunResponse)
def start_run(req: RunStartRequest, db: Session = Depends(get_db)):
    repo = RunRepository(db)
    
    # 如果提供了 test_case_id，验证并加载 test case
    test_case = None
    if req.test_case_id:
        test_case_repo = TestCaseRepository(db)
        test_case = test_case_repo.get(req.test_case_id)
        if not test_case:
            raise HTTPException(status_code=404, detail="Test case not found")
    
    # 如果提供了 evaluation_id，验证 evaluation
    if req.evaluation_id:
        eval_repo = EvaluationRepository(db)
        evaluation = eval_repo.get(req.evaluation_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")
    
    # 创建 run，自动关联 test_case 的 query
    run_metadata = req.metadata or {}
    run = repo.create(
        name=req.name,
        evaluation_id=req.evaluation_id,
        test_case_id=req.test_case_id,
        query=test_case.query if test_case else None,
        metadata=run_metadata
    )
    
    # 如果 test_case 有 gold 数据，自动关联
    if test_case and test_case.gold_chunk_ids:
        gold_repo = GoldChunkRepository(db)
        gold_repo.bulk_create(run.id, test_case.gold_chunk_ids)
    
    # 如果 test_case 有 GraphRAG gold 数据（gold_path, gold_nodes），存储到 run.metadata
    if test_case and (test_case.gold_path or test_case.gold_nodes):
        if test_case.gold_path:
            run_metadata["gold_path"] = test_case.gold_path
        if test_case.gold_nodes:
            run_metadata["gold_nodes"] = test_case.gold_nodes
        # 更新 run metadata
        run.metadata_ = run_metadata
        db.commit()
        db.refresh(run)
    
    # 如果 test_case 有 gold_answer，存储到 run.answer（稍后用于对比）
    # 注意：这里不直接存储 gold_answer 到 run.answer，因为 answer 字段用于实际生成的答案
    # gold_answer 保留在 test_case 中，评测时会读取
    
    return RunResponse(
        id=run.id, name=run.name, status=run.status,
        metadata=run.metadata_, started_at=run.started_at, ended_at=run.ended_at
    )


@router.post("/run/{run_id}/end", response_model=RunResponse)
def end_run(run_id: UUID, req: RunEndRequest, db: Session = Depends(get_db)):
    repo = RunRepository(db)
    run = repo.end(run_id, status=req.status)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse(
        id=run.id, name=run.name, status=run.status,
        metadata=run.metadata_, started_at=run.started_at, ended_at=run.ended_at
    )


@router.post("/span/start", response_model=SpanResponse)
def start_span(req: SpanStartRequest, db: Session = Depends(get_db)):
    repo = SpanRepository(db)
    span = repo.create(
        run_id=req.run_id, name=req.name, parent_span_id=req.parent_span_id,
        input=req.input, metadata=req.metadata
    )
    return SpanResponse(
        id=span.id, run_id=span.run_id, name=span.name,
        parent_span_id=span.parent_span_id, input=span.input, output=span.output,
        metadata=span.metadata_, started_at=span.started_at, ended_at=span.ended_at
    )


@router.post("/span/{span_id}/end", response_model=SpanResponse)
def end_span(span_id: UUID, req: SpanEndRequest, db: Session = Depends(get_db)):
    repo = SpanRepository(db)
    span = repo.end(span_id, output=req.output)
    if not span:
        raise HTTPException(status_code=404, detail="Span not found")
    return SpanResponse(
        id=span.id, run_id=span.run_id, name=span.name,
        parent_span_id=span.parent_span_id, input=span.input, output=span.output,
        metadata=span.metadata_, started_at=span.started_at, ended_at=span.ended_at
    )


@router.post("/event", response_model=EventResponse)
def create_event(req: EventCreateRequest, db: Session = Depends(get_db)):
    repo = EventRepository(db)
    event = repo.create(run_id=req.run_id, name=req.name, data=req.data, span_id=req.span_id)
    return EventResponse(
        id=event.id, run_id=event.run_id, span_id=event.span_id,
        name=event.name, data=event.data, created_at=event.created_at
    )


@router.post("/metric", response_model=MetricResponse)
def create_metric(req: MetricCreateRequest, db: Session = Depends(get_db)):
    repo = MetricRepository(db)
    metric = repo.create(
        run_id=req.run_id, name=req.name, value=req.value,
        value_json=req.value_json, metadata=req.metadata
    )
    return MetricResponse(
        id=metric.id, run_id=metric.run_id, name=metric.name,
        value=metric.value, value_json=metric.value_json,
        metadata=metric.metadata_, created_at=metric.created_at
    )


@router.get("/run/{run_id}/rag-metrics", response_model=RAGMetricsResponse)
def get_rag_metrics(run_id: UUID, db: Session = Depends(get_db)):
    run_repo = RunRepository(db)
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return compute_rag_metrics(run_id, db)


@router.get("/run/{run_id}/graph")
def get_run_graph(run_id: UUID, db: Session = Depends(get_db)):
    run_repo = RunRepository(db)
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    graph = build_run_graph(run_id, db)
    return graph.to_dict()


@router.get("/run/{run_id}/chunk-attribution")
def get_chunk_attribution(run_id: UUID, db: Session = Depends(get_db)):
    run_repo = RunRepository(db)
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    attributions = compute_chunk_attribution(run_id, db)
    return {
        "run_id": str(run_id),
        "attributions": [
            {
                "chunk_id": a.chunk_id,
                "retrieved": a.retrieved,
                "used": a.used,
                "retrieval_score": a.retrieval_score,
                "retrieval_span_id": a.retrieval_span_id,
                "answer_span_id": a.answer_span_id
            }
            for a in attributions
        ]
    }


@router.get("/runs/diff")
def diff_runs(
    run_id_a: UUID = Query(...),
    run_id_b: UUID = Query(...),
    db: Session = Depends(get_db)
):
    """对比两个 run 的 retrieval 差异（核心功能）"""
    run_repo = RunRepository(db)
    
    run_a = run_repo.get(run_id_a)
    run_b = run_repo.get(run_id_b)
    if not run_a or not run_b:
        raise HTTPException(status_code=404, detail="Run not found")
    
    metrics_a = compute_rag_metrics(run_id_a, db)
    metrics_b = compute_rag_metrics(run_id_b, db)
    
    retrieved_a = extract_retrieval_results(run_id_a, db)
    retrieved_b = extract_retrieval_results(run_id_b, db)
    
    version_a = extract_version_info(run_id_a, db)
    version_b = extract_version_info(run_id_b, db)
    
    retrieval_diff = compute_retrieval_diff(retrieved_a, retrieved_b)
    
    return {
        "run_a": {
            "id": str(run_id_a),
            "version": {
                "splitter_version": version_a.splitter_version,
                "embedding_model": version_a.embedding_model,
                "vector_db": version_a.vector_db,
                "index_version": version_a.index_version
            },
            "metrics": {
                "retrieval_used_ratio": metrics_a.retrieval_used_ratio,
                "total_retrieved_chunks": metrics_a.total_retrieved_chunks,
                "used_chunks": metrics_a.used_chunks,
                "gold_metrics": metrics_a.gold_metrics
            }
        },
        "run_b": {
            "id": str(run_id_b),
            "version": {
                "splitter_version": version_b.splitter_version,
                "embedding_model": version_b.embedding_model,
                "vector_db": version_b.vector_db,
                "index_version": version_b.index_version
            },
            "metrics": {
                "retrieval_used_ratio": metrics_b.retrieval_used_ratio,
                "total_retrieved_chunks": metrics_b.total_retrieved_chunks,
                "used_chunks": metrics_b.used_chunks,
                "gold_metrics": metrics_b.gold_metrics
            }
        },
        "retrieval_diff": {
            "only_in_a": retrieval_diff["only_in_a"],
            "only_in_b": retrieval_diff["only_in_b"],
            "in_both": retrieval_diff["in_both"],
            "rank_deltas": retrieval_diff["rank_deltas"],
            "total_a": retrieval_diff["total_a"],
            "total_b": retrieval_diff["total_b"]
        },
        "metrics_diff": {
            "retrieval_used_ratio_delta": (metrics_b.retrieval_used_ratio or 0) - (metrics_a.retrieval_used_ratio or 0),
            "used_chunks_delta": metrics_b.used_chunks - metrics_a.used_chunks,
            "pollution_rate_delta": (metrics_b.context_pollution_rate or 0) - (metrics_a.context_pollution_rate or 0)
        },
        "version_changes": {
            "splitter_version_changed": version_a.splitter_version != version_b.splitter_version,
            "embedding_model_changed": version_a.embedding_model != version_b.embedding_model,
            "vector_db_changed": version_a.vector_db != version_b.vector_db,
            "index_version_changed": version_a.index_version != version_b.index_version
        }
    }

