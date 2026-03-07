"""
GraphRAG 指标计算
专注于推理路径质量评测
"""
import logging
from uuid import UUID

logger = logging.getLogger(__name__)
from typing import Optional, Dict, List, Set
from sqlalchemy.orm import Session
from tracelens.storage.repository import RunRepository, MetricRepository
from tracelens.storage.graph_repository import (
    GraphNodeRepository,
    GraphEdgeRepository,
    ReasoningTraceRepository
)


def compute_path_exists(run_id: UUID, db: Session) -> bool:
    """
    指标1: Path Existence
    判断是否存在推理路径
    """
    trace_repo = ReasoningTraceRepository(db)
    selected_path = trace_repo.get_selected_path(run_id)
    return len(selected_path) > 0


def compute_reasoning_hops(run_id: UUID, db: Session) -> int:
    """
    指标2: Reasoning Hops
    计算推理跳数
    """
    trace_repo = ReasoningTraceRepository(db)
    selected_path = trace_repo.get_selected_path(run_id)
    return len(selected_path)


def compute_connectivity_score(run_id: UUID, db: Session) -> float:
    """
    指标3: Connectivity Score
    计算检索到的节点是否形成连通子图
    使用并查集算法计算最大连通分量
    """
    node_repo = GraphNodeRepository(db)
    edge_repo = GraphEdgeRepository(db)
    
    nodes = node_repo.get_by_run(run_id)
    edges = edge_repo.get_by_run(run_id)
    
    if len(nodes) == 0:
        return 0.0
    
    # 构建邻接表
    adj = {}
    for node in nodes:
        adj[node.node_id] = []
    
    for edge in edges:
        if edge.from_node in adj:
            adj[edge.from_node].append(edge.to_node)
        if edge.to_node in adj:
            adj[edge.to_node].append(edge.from_node)
    
    # BFS 找最大连通分量
    visited = set()
    max_component_size = 0
    
    for node_id in adj:
        if node_id not in visited:
            # BFS
            queue = [node_id]
            component = set()
            
            while queue:
                curr = queue.pop(0)
                if curr in visited:
                    continue
                visited.add(curr)
                component.add(curr)
                
                for neighbor in adj.get(curr, []):
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            max_component_size = max(max_component_size, len(component))
    
    # 连通度 = 最大连通分量 / 总节点数
    return max_component_size / len(nodes) if len(nodes) > 0 else 0.0


def compute_path_coverage(run_id: UUID, gold_path: List[str], db: Session) -> float:
    """
    指标4: Path Coverage（需要 gold path）
    计算选中路径对 gold path 的覆盖度
    """
    trace_repo = ReasoningTraceRepository(db)
    selected_path = trace_repo.get_selected_path(run_id)
    
    if len(gold_path) == 0:
        return 0.0
    
    # 提取选中路径的节点
    selected_nodes = set()
    for trace in selected_path:
        selected_nodes.add(trace.from_node)
        selected_nodes.add(trace.to_node)
    
    # 计算交集
    gold_nodes = set(gold_path)
    intersection = selected_nodes & gold_nodes
    
    return len(intersection) / len(gold_nodes)


def compute_branch_explosion_ratio(run_id: UUID, db: Session) -> float:
    """
    指标5: Branch Explosion Ratio
    计算剪枝策略是否有效
    """
    node_repo = GraphNodeRepository(db)
    trace_repo = ReasoningTraceRepository(db)
    
    all_nodes = node_repo.get_by_run(run_id)
    selected_path = trace_repo.get_selected_path(run_id)
    
    if len(selected_path) == 0:
        return 0.0
    
    # 选中路径的节点数（去重）
    selected_nodes = set()
    for trace in selected_path:
        selected_nodes.add(trace.from_node)
        selected_nodes.add(trace.to_node)
    
    # 分支爆炸比 = 总扩展节点 / 选中路径节点
    return len(all_nodes) / len(selected_nodes) if len(selected_nodes) > 0 else 0.0


def compute_path_relevance_score(run_id: UUID, db: Session, llm_client=None) -> Optional[float]:
    """
    指标6: Path Relevance Score（使用 LLM Judge）
    判断推理路径是否逻辑上支持回答 query
    """
    if llm_client is None:
        return None
    
    run_repo = RunRepository(db)
    trace_repo = ReasoningTraceRepository(db)
    
    run = run_repo.get(run_id)
    if not run or not run.query or not run.answer:
        return None
    
    selected_path = trace_repo.get_selected_path(run_id)
    if len(selected_path) == 0:
        return None
    
    # 构建路径描述
    path_desc = " → ".join([
        f"{t.from_node} --[{t.relation}]-> {t.to_node}"
        for t in selected_path
    ])
    
    # LLM Prompt
    prompt = f"""Please evaluate whether the reasoning path logically supports answering the query.

Query: {run.query}

Reasoning Path:
{path_desc}

Answer: {run.answer}

Provide a relevance score (0.0 to 1.0) where:
- 0.0: Path is irrelevant or illogical
- 0.5: Path is partially relevant
- 1.0: Path strongly supports the answer

Return ONLY a number between 0.0 and 1.0.
Score:"""
    
    try:
        response = llm_client(prompt)
        
        # 解析分数
        import re
        numbers = re.findall(r'0?\.\d+|[01]\.?\d*', response)
        if numbers:
            score = float(numbers[0])
            return max(0.0, min(1.0, score))
    except Exception as e:
        logger.warning("LLM evaluation failed: %s", e)

    return None


def compute_all_graph_metrics(
    run_id: UUID,
    db: Session,
    gold_path: Optional[List[str]] = None,
    include_semantic: bool = False,
    llm_client=None
) -> Dict:
    """
    计算所有 GraphRAG 指标
    
    返回结构：
    {
        "structural": {
            "path_exists": bool,
            "reasoning_hops": int,
            "connectivity_score": float
        },
        "quality": {
            "path_coverage": float,  # 如果有 gold_path
            "branch_explosion_ratio": float
        },
        "semantic": {
            "path_relevance_score": float  # 如果 include_semantic=True
        }
    }
    """
    metrics = {
        "structural": {},
        "quality": {},
        "semantic": {}
    }
    
    # 结构性指标（必须计算）
    metrics["structural"]["path_exists"] = compute_path_exists(run_id, db)
    metrics["structural"]["reasoning_hops"] = compute_reasoning_hops(run_id, db)
    metrics["structural"]["connectivity_score"] = compute_connectivity_score(run_id, db)
    
    # 路径质量指标
    metrics["quality"]["branch_explosion_ratio"] = compute_branch_explosion_ratio(run_id, db)
    
    if gold_path:
        metrics["quality"]["path_coverage"] = compute_path_coverage(run_id, gold_path, db)
    
    # 语义合理性指标（可选）
    if include_semantic and llm_client:
        metrics["semantic"]["path_relevance_score"] = compute_path_relevance_score(run_id, db, llm_client)
    
    metric_repo = MetricRepository(db)
    for name, value in metrics["structural"].items():
        if isinstance(value, bool):
            value = 1.0 if value else 0.0
        metric_repo.upsert(run_id, f"graph_{name}", value=float(value), metadata={"type": "structural"})
    for name, value in metrics["quality"].items():
        if value is not None:
            metric_repo.upsert(run_id, f"graph_{name}", value=float(value), metadata={"type": "quality"})
    for name, value in metrics["semantic"].items():
        if value is not None:
            metric_repo.upsert(run_id, f"graph_{name}", value=float(value), metadata={"type": "semantic"})
    
    return metrics

