"""
GraphRAG 批量评测 API Schemas
"""
from uuid import UUID
from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class MetricStats(BaseModel):
    """指标统计信息"""
    avg: Optional[float] = None
    p50: Optional[float] = None
    p95: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None


class GraphEvaluationMetricsResponse(BaseModel):
    """GraphRAG 评测任务聚合指标响应"""
    evaluation_id: UUID
    name: str
    version_id: str
    total_runs: int
    completed_runs: int
    status: str
    aggregate_metrics: Dict[str, Dict[str, MetricStats]]  # category -> metric_name -> stats
    per_query_metrics: Optional[List[Dict[str, Any]]] = None


class MetricDelta(BaseModel):
    """指标差异"""
    avg_a: float
    avg_b: float
    delta: float
    percent_change: Optional[float] = None
    p50_a: Optional[float] = None
    p50_b: Optional[float] = None
    p95_a: Optional[float] = None
    p95_b: Optional[float] = None


class EvaluationInfo(BaseModel):
    """评测任务基本信息"""
    id: UUID
    version_id: str
    name: str


class GraphEvaluationComparisonResponse(BaseModel):
    """GraphRAG 评测任务对比响应"""
    evaluation_a: EvaluationInfo
    evaluation_b: EvaluationInfo
    metrics_delta: Dict[str, Dict[str, MetricDelta]]  # category -> metric_name -> delta_info
    per_query_comparison: Optional[List[Dict[str, Any]]] = None

