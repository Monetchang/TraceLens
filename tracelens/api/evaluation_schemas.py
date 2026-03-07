from uuid import UUID
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


# ==================== 请求模型 ====================

class TestSuiteCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class TestCaseItem(BaseModel):
    query: str
    gold_answer: Optional[str] = None
    gold_chunk_ids: Optional[List[str]] = None
    gold_doc_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class TestCaseBulkCreateRequest(BaseModel):
    test_cases: List[TestCaseItem]


class EvaluationCreateRequest(BaseModel):
    name: str
    test_suite_id: UUID
    version_id: str
    metadata: Optional[Dict[str, Any]] = None


# ==================== 响应模型 ====================

class TestSuiteResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    test_case_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class TestCaseResponse(BaseModel):
    id: UUID
    test_suite_id: UUID
    query: str
    gold_answer: Optional[str]
    gold_chunk_ids: Optional[List[str]]
    gold_doc_ids: Optional[List[str]]
    metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class EvaluationResponse(BaseModel):
    id: UUID
    name: str
    test_suite_id: UUID
    version_id: str
    status: str
    total_runs: int
    completed_runs: int
    failed_runs: int
    metadata: Dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class EvaluationStatusResponse(BaseModel):
    evaluation_id: UUID
    status: str
    total_test_cases: int
    total_runs: int
    completed_runs: int
    failed_runs: int
    progress: float  # 0.0 - 1.0
    metrics_computation_status: Optional[str] = None  # pending | computing | done


class MetricStats(BaseModel):
    avg: Optional[float]
    p50: Optional[float]
    p95: Optional[float]
    min: Optional[float]
    max: Optional[float]


class PerQueryMetric(BaseModel):
    test_case_id: UUID
    query: str
    run_id: UUID
    metrics: Dict[str, float]


class EvaluationMetricsResponse(BaseModel):
    evaluation_id: UUID
    version_id: str
    total_runs: int
    completed_runs: int
    aggregate_metrics: Dict[str, MetricStats]  # metric_name -> stats
    per_query_metrics: Optional[List[PerQueryMetric]] = None


class MetricDelta(BaseModel):
    value_a: Optional[float]
    value_b: Optional[float]
    delta: Optional[float]
    percent_change: Optional[float]


class PerQueryComparison(BaseModel):
    test_case_id: UUID
    query: str
    run_id_a: Optional[UUID]
    run_id_b: Optional[UUID]
    metrics_delta: Dict[str, MetricDelta]  # metric_name -> delta


class EvaluationComparisonResponse(BaseModel):
    evaluation_a: Dict[str, Any]  # {id, version_id, name}
    evaluation_b: Dict[str, Any]  # {id, version_id, name}
    metrics_delta: Dict[str, MetricStats]  # aggregated delta stats
    per_query_comparison: Optional[List[PerQueryComparison]] = None

