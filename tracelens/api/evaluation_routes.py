from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from tracelens.storage.database import get_db
from tracelens.storage.evaluation_repository import (
    TestSuiteRepository, TestCaseRepository, EvaluationRepository
)
from tracelens.api.evaluation_schemas import (
    TestSuiteCreateRequest, TestCaseBulkCreateRequest, EvaluationCreateRequest,
    TestSuiteResponse, TestCaseResponse, EvaluationResponse,
    EvaluationStatusResponse, EvaluationMetricsResponse, EvaluationComparisonResponse,
    MetricStats, PerQueryMetric, PerQueryComparison, MetricDelta
)
from tracelens.api.graph_evaluation_schemas import (
    GraphEvaluationMetricsResponse, GraphEvaluationComparisonResponse
)
from tracelens.core.evaluation_metrics import compute_evaluation_metrics, compute_evaluation_comparison
from tracelens.core.graph_evaluation_metrics import (
    compute_graph_evaluation_metrics, compute_graph_evaluation_comparison
)


router = APIRouter(prefix="/api/v1")


# ==================== 测试集管理 ====================

@router.post("/test_suite", response_model=TestSuiteResponse)
def create_test_suite(req: TestSuiteCreateRequest, db: Session = Depends(get_db)):
    """创建测试集"""
    suite_repo = TestSuiteRepository(db)
    suite = suite_repo.create(req.name, req.description)
    
    return TestSuiteResponse(
        id=suite.id,
        name=suite.name,
        description=suite.description,
        test_case_count=0,
        created_at=suite.created_at
    )


@router.get("/test_suite/{suite_id}", response_model=TestSuiteResponse)
def get_test_suite(suite_id: UUID, db: Session = Depends(get_db)):
    """获取测试集详情"""
    suite_repo = TestSuiteRepository(db)
    suite = suite_repo.get(suite_id)
    
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    
    test_case_count = suite_repo.get_test_case_count(suite_id)
    
    return TestSuiteResponse(
        id=suite.id,
        name=suite.name,
        description=suite.description,
        test_case_count=test_case_count,
        created_at=suite.created_at
    )


@router.post("/test_suite/{suite_id}/test_cases")
def bulk_create_test_cases(
    suite_id: UUID,
    req: TestCaseBulkCreateRequest,
    db: Session = Depends(get_db)
):
    """批量导入测试用例"""
    suite_repo = TestSuiteRepository(db)
    suite = suite_repo.get(suite_id)
    
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    
    test_case_repo = TestCaseRepository(db)
    test_cases_data = [tc.model_dump() for tc in req.test_cases]
    created_cases = test_case_repo.bulk_create(suite_id, test_cases_data)
    
    return {
        "status": "ok",
        "created_count": len(created_cases),
        "test_case_ids": [str(tc.id) for tc in created_cases]
    }


@router.get("/test_suite/{suite_id}/test_cases", response_model=list[TestCaseResponse])
def get_test_cases(
    suite_id: UUID,
    limit: int = Query(1000, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """获取测试集的所有测试用例"""
    suite_repo = TestSuiteRepository(db)
    suite = suite_repo.get(suite_id)
    
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    
    test_case_repo = TestCaseRepository(db)
    test_cases = test_case_repo.get_by_suite(suite_id, limit, offset)
    
    return [
        TestCaseResponse(
            id=tc.id,
            test_suite_id=tc.test_suite_id,
            query=tc.query,
            gold_answer=tc.gold_answer,
            gold_chunk_ids=tc.gold_chunk_ids,
            gold_doc_ids=tc.gold_doc_ids,
            metadata=tc.metadata_,
            created_at=tc.created_at
        )
        for tc in test_cases
    ]


# ==================== 评测任务管理 ====================

@router.post("/evaluation", response_model=EvaluationResponse)
def create_evaluation(req: EvaluationCreateRequest, db: Session = Depends(get_db)):
    """创建评测任务"""
    suite_repo = TestSuiteRepository(db)
    suite = suite_repo.get(req.test_suite_id)
    
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    
    eval_repo = EvaluationRepository(db)
    evaluation = eval_repo.create(req.name, req.test_suite_id, req.version_id, req.metadata)
    
    return EvaluationResponse(
        id=evaluation.id,
        name=evaluation.name,
        test_suite_id=evaluation.test_suite_id,
        version_id=evaluation.version_id,
        status=evaluation.status,
        total_runs=0,
        completed_runs=0,
        failed_runs=0,
        metadata=evaluation.metadata_,
        created_at=evaluation.created_at,
        completed_at=evaluation.completed_at
    )


@router.get("/evaluation/{evaluation_id}", response_model=EvaluationResponse)
def get_evaluation(evaluation_id: UUID, db: Session = Depends(get_db)):
    """获取评测任务详情"""
    eval_repo = EvaluationRepository(db)
    evaluation = eval_repo.get(evaluation_id)
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    total_runs = eval_repo.get_run_count(evaluation_id)
    completed_runs = eval_repo.get_run_count(evaluation_id, status="success")
    failed_runs = eval_repo.get_run_count(evaluation_id, status="error")
    
    return EvaluationResponse(
        id=evaluation.id,
        name=evaluation.name,
        test_suite_id=evaluation.test_suite_id,
        version_id=evaluation.version_id,
        status=evaluation.status,
        total_runs=total_runs,
        completed_runs=completed_runs,
        failed_runs=failed_runs,
        metadata=evaluation.metadata_,
        created_at=evaluation.created_at,
        completed_at=evaluation.completed_at
    )


@router.get("/evaluation/{evaluation_id}/test_cases", response_model=list[TestCaseResponse])
def get_evaluation_test_cases(evaluation_id: UUID, db: Session = Depends(get_db)):
    """获取评测任务的测试用例（供 RAG 系统遍历）"""
    eval_repo = EvaluationRepository(db)
    evaluation = eval_repo.get(evaluation_id)
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    test_case_repo = TestCaseRepository(db)
    test_cases = test_case_repo.get_by_suite(evaluation.test_suite_id)
    
    return [
        TestCaseResponse(
            id=tc.id,
            test_suite_id=tc.test_suite_id,
            query=tc.query,
            gold_answer=tc.gold_answer,
            gold_chunk_ids=tc.gold_chunk_ids,
            gold_doc_ids=tc.gold_doc_ids,
            metadata=tc.metadata_,
            created_at=tc.created_at
        )
        for tc in test_cases
    ]


@router.get("/evaluation/{evaluation_id}/status", response_model=EvaluationStatusResponse)
def get_evaluation_status(evaluation_id: UUID, db: Session = Depends(get_db)):
    """获取评测进度"""
    eval_repo = EvaluationRepository(db)
    suite_repo = TestSuiteRepository(db)
    
    evaluation = eval_repo.get(evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    total_test_cases = suite_repo.get_test_case_count(evaluation.test_suite_id)
    total_runs = eval_repo.get_run_count(evaluation_id)
    completed_runs = eval_repo.get_run_count(evaluation_id, status="success")
    failed_runs = eval_repo.get_run_count(evaluation_id, status="error")
    
    progress = completed_runs / total_test_cases if total_test_cases > 0 else 0.0
    
    return EvaluationStatusResponse(
        evaluation_id=evaluation_id,
        status=evaluation.status,
        total_test_cases=total_test_cases,
        total_runs=total_runs,
        completed_runs=completed_runs,
        failed_runs=failed_runs,
        progress=progress
    )


@router.get("/evaluation/{evaluation_id}/metrics", response_model=EvaluationMetricsResponse)
def get_evaluation_metrics(
    evaluation_id: UUID,
    similarity_mode: str = Query("lexical", description="相似度计算模式：lexical, embedding, llm"),
    include_per_query: bool = Query(False, description="是否包含每个问题的详细指标"),
    db: Session = Depends(get_db)
):
    """获取评测任务的聚合指标"""
    eval_repo = EvaluationRepository(db)
    evaluation = eval_repo.get(evaluation_id)
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    try:
        metrics_data = compute_evaluation_metrics(
            evaluation_id, db, similarity_mode, include_per_query
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute metrics: {str(e)}")
    
    # 转换为响应格式
    aggregate_metrics = {}
    for metric_name, stats in metrics_data["aggregate_metrics"].items():
        aggregate_metrics[metric_name] = MetricStats(**stats)
    
    per_query_metrics = None
    if include_per_query and metrics_data["per_query_metrics"]:
        per_query_metrics = [
            PerQueryMetric(**item) for item in metrics_data["per_query_metrics"]
        ]
    
    return EvaluationMetricsResponse(
        evaluation_id=evaluation_id,
        version_id=metrics_data["version_id"],
        total_runs=metrics_data["total_runs"],
        completed_runs=metrics_data["completed_runs"],
        aggregate_metrics=aggregate_metrics,
        per_query_metrics=per_query_metrics
    )


# ==================== 版本对比 ====================

@router.get("/evaluation/compare", response_model=EvaluationComparisonResponse)
def compare_evaluations(
    eval_a: UUID = Query(..., description="第一个评测任务 ID"),
    eval_b: UUID = Query(..., description="第二个评测任务 ID"),
    similarity_mode: str = Query("lexical", description="相似度计算模式：lexical, embedding, llm"),
    include_per_query: bool = Query(False, description="是否包含每个问题的详细对比"),
    db: Session = Depends(get_db)
):
    """对比两个评测任务"""
    try:
        comparison_data = compute_evaluation_comparison(
            eval_a, eval_b, db, similarity_mode, include_per_query
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare evaluations: {str(e)}")
    
    # 转换为响应格式
    metrics_delta = {}
    for metric_name, delta_stats in comparison_data["metrics_delta"].items():
        # 保持原始字典格式，因为包含多个字段
        metrics_delta[metric_name] = delta_stats
    
    per_query_comparison = None
    if include_per_query and comparison_data["per_query_comparison"]:
        per_query_comparison = []
        for item in comparison_data["per_query_comparison"]:
            metrics_delta_dict = {}
            for metric_name, delta in item["metrics_delta"].items():
                metrics_delta_dict[metric_name] = MetricDelta(**delta)
            
            per_query_comparison.append(PerQueryComparison(
                test_case_id=item["test_case_id"],
                query=item["query"],
                run_id_a=item["run_id_a"],
                run_id_b=item["run_id_b"],
                metrics_delta=metrics_delta_dict
            ))
    
    return EvaluationComparisonResponse(
        evaluation_a=comparison_data["evaluation_a"],
        evaluation_b=comparison_data["evaluation_b"],
        metrics_delta=metrics_delta,
        per_query_comparison=per_query_comparison
    )


# ==================== GraphRAG 评测 ====================

@router.get("/evaluation/{evaluation_id}/graph_metrics", response_model=GraphEvaluationMetricsResponse)
def get_graph_evaluation_metrics(
    evaluation_id: UUID,
    include_semantic: bool = Query(False, description="是否包含语义指标（LLM Judge）"),
    include_per_query: bool = Query(False, description="是否包含每个问题的详细指标"),
    db: Session = Depends(get_db)
):
    """获取 GraphRAG 评测任务的聚合指标"""
    eval_repo = EvaluationRepository(db)
    evaluation = eval_repo.get(evaluation_id)
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    try:
        metrics_data = compute_graph_evaluation_metrics(
            evaluation_id, db, 
            include_semantic=include_semantic,
            include_per_query=include_per_query,
            llm_client=None  # TODO: 添加 LLM 客户端支持
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute graph metrics: {str(e)}")
    
    return GraphEvaluationMetricsResponse(**metrics_data)


@router.get("/evaluation/graph_compare", response_model=GraphEvaluationComparisonResponse)
def compare_graph_evaluations(
    eval_a: UUID = Query(..., description="第一个评测任务 ID"),
    eval_b: UUID = Query(..., description="第二个评测任务 ID"),
    include_semantic: bool = Query(False, description="是否包含语义指标"),
    include_per_query: bool = Query(False, description="是否包含每个问题的详细对比"),
    db: Session = Depends(get_db)
):
    """对比两个 GraphRAG 评测任务"""
    try:
        comparison_data = compute_graph_evaluation_comparison(
            eval_a, eval_b, db,
            include_semantic=include_semantic,
            include_per_query=include_per_query,
            llm_client=None  # TODO: 添加 LLM 客户端支持
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare graph evaluations: {str(e)}")
    
    return GraphEvaluationComparisonResponse(**comparison_data)

