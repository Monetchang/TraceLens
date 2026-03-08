"""
GraphRAG API Routes
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from tracelens.storage.database import get_db
from tracelens.api.dependencies import verify_api_key
from tracelens.storage.repository import RunRepository
from tracelens.storage.graph_repository import (
    GraphNodeRepository,
    GraphEdgeRepository,
    ReasoningTraceRepository
)
from tracelens.api.graph_schemas import (
    GraphExpandRequest,
    PathSelectedRequest,
    GraphMetricsResponse,
    ReasoningPathResponse
)

router = APIRouter(prefix="/api/v1")


@router.post("/graph/expand")
def graph_expand(req: GraphExpandRequest, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """上报图扩展事件"""
    run_repo = RunRepository(db)
    run = run_repo.get(req.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # 创建节点（如果不存在）
    node_repo = GraphNodeRepository(db)
    if not node_repo.get_by_node_id(req.run_id, req.from_node):
        node_repo.create(req.run_id, req.from_node, "entity")
    if not node_repo.get_by_node_id(req.run_id, req.to_node):
        node_repo.create(req.run_id, req.to_node, "entity")
    
    # 创建边
    edge_repo = GraphEdgeRepository(db)
    edge_repo.create(req.run_id, req.from_node, req.to_node, req.relation)
    
    # 创建推理轨迹
    trace_repo = ReasoningTraceRepository(db)
    trace_repo.create(
        req.run_id,
        req.step_index,
        req.from_node,
        req.to_node,
        req.relation,
        is_selected=False
    )
    
    return {"status": "ok"}


@router.post("/graph/path/selected")
def path_selected(req: PathSelectedRequest, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """上报路径选择事件"""
    run_repo = RunRepository(db)
    run = run_repo.get(req.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    trace_repo = ReasoningTraceRepository(db)
    all_traces = trace_repo.get_by_run(req.run_id)
    
    # 找到匹配 path 的 traces
    selected_indices = []
    for i in range(len(req.path) - 1):
        from_node = req.path[i]
        to_node = req.path[i + 1]
        
        for trace in all_traces:
            if trace.from_node == from_node and trace.to_node == to_node:
                selected_indices.append(trace.step_index)
                break
    
    # 标记为选中
    if selected_indices:
        trace_repo.mark_as_selected(req.run_id, selected_indices)
    
    return {"status": "ok"}


@router.get("/run/{run_id}/graph-metrics", response_model=GraphMetricsResponse)
def get_graph_metrics(
    run_id: UUID,
    include_semantic: bool = False,
    include_grounding: bool = True,
    db: Session = Depends(get_db)
):
    """获取 GraphRAG 指标"""
    from tracelens.core.graph_metrics import compute_all_graph_metrics

    run_repo = RunRepository(db)
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    metrics = compute_all_graph_metrics(
        run_id, db,
        include_semantic=include_semantic,
        include_grounding=include_grounding
    )

    return GraphMetricsResponse(
        run_id=run_id,
        structural_metrics=metrics.get("structural", {}),
        quality_metrics=metrics.get("quality"),
        semantic_metrics=metrics.get("semantic") if include_semantic else None,
        grounding_metrics=metrics.get("grounding") if include_grounding else None
    )


@router.get("/run/{run_id}/reasoning-path", response_model=ReasoningPathResponse)
def get_reasoning_path(run_id: UUID, db: Session = Depends(get_db)):
    """获取推理路径"""
    run_repo = RunRepository(db)
    run = run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    trace_repo = ReasoningTraceRepository(db)
    selected_traces = trace_repo.get_selected_path(run_id)
    all_traces = trace_repo.get_by_run(run_id)
    
    selected_path = [
        {
            "from_node": t.from_node,
            "to_node": t.to_node,
            "relation": t.relation,
            "step_index": t.step_index
        }
        for t in selected_traces
    ]
    
    all_path = [
        {
            "from_node": t.from_node,
            "to_node": t.to_node,
            "relation": t.relation,
            "step_index": t.step_index,
            "is_selected": t.is_selected
        }
        for t in all_traces
    ]
    
    return ReasoningPathResponse(
        run_id=run_id,
        selected_path=selected_path,
        all_traces=all_path
    )

