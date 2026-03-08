"""
GraphRAG API Schemas
"""
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel


class GraphExpandRequest(BaseModel):
    """图扩展事件"""
    run_id: UUID
    from_node: str
    to_node: str
    relation: str
    step_index: int


class PathSelectedRequest(BaseModel):
    """路径选择事件"""
    run_id: UUID
    path: List[str]  # node_ids


class GraphMetricsResponse(BaseModel):
    """GraphRAG 指标响应"""
    run_id: UUID
    structural_metrics: dict
    quality_metrics: Optional[dict] = None
    semantic_metrics: Optional[dict] = None
    grounding_metrics: Optional[dict] = None


class ReasoningPathResponse(BaseModel):
    """推理路径响应"""
    run_id: UUID
    selected_path: List[dict]  # [{from_node, to_node, relation, step_index}]
    all_traces: List[dict]  # 所有推理轨迹

