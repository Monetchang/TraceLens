"""
GraphRAG 指标计算
专注于推理路径质量评测
"""
import logging
import re
from dataclasses import dataclass
from uuid import UUID

logger = logging.getLogger(__name__)
from typing import Optional, Dict, List, Set, Any
from sqlalchemy.orm import Session
from tracelens.storage.repository import RunRepository, MetricRepository
from tracelens.storage.graph_repository import (
    GraphNodeRepository,
    GraphEdgeRepository,
    ReasoningTraceRepository
)
from tracelens.storage.graph_models import ReasoningTrace

# 弱关系词，增加无关倾向
WEAK_RELATIONS = {"related_to", "mentions", "similar_to", "other", "unknown", ""}


@dataclass
class GraphEdge:
    from_node: str
    to_node: str
    relation: str
    step_index: Optional[int] = None


@dataclass
class GraphBranch:
    from_node: str
    to_node: str
    relation: str
    step_index: Optional[int]
    text: str


@dataclass
class GraphMetricsContext:
    run_id: UUID
    query: Optional[str]
    answer: Optional[str]
    selected_path_nodes: List[str]
    selected_path_edges: List[GraphEdge]
    explored_nodes: List[str]
    explored_edges: List[GraphEdge]
    explored_branches: List[GraphBranch]
    gold_nodes: Optional[List[str]]


def _trace_to_edge(t: ReasoningTrace) -> GraphEdge:
    return GraphEdge(t.from_node, t.to_node, t.relation or "", t.step_index)


def _trace_to_branch(t: ReasoningTrace) -> GraphBranch:
    rel = t.relation or ""
    text = f"{t.from_node} --{rel}--> {t.to_node}"
    return GraphBranch(t.from_node, t.to_node, rel, t.step_index, text)


def build_graph_metrics_context(
    run_id: UUID, db: Session, gold_nodes: Optional[List[str]] = None
) -> GraphMetricsContext:
    run_repo = RunRepository(db)
    node_repo = GraphNodeRepository(db)
    edge_repo = GraphEdgeRepository(db)
    trace_repo = ReasoningTraceRepository(db)

    run = run_repo.get(run_id)
    query = run.query if run else None
    answer = run.answer if run else None

    selected_traces = trace_repo.get_selected_path_edges(run_id)
    all_traces = trace_repo.get_explored_branches(run_id)

    selected_path_nodes = []
    for t in selected_traces:
        if not selected_path_nodes:
            selected_path_nodes = [t.from_node, t.to_node]
        else:
            if selected_path_nodes[-1] == t.from_node:
                selected_path_nodes.append(t.to_node)
            elif selected_path_nodes[0] == t.to_node:
                selected_path_nodes.insert(0, t.from_node)
            else:
                selected_path_nodes.extend([t.from_node, t.to_node])
    if selected_path_nodes:
        selected_path_nodes = list(dict.fromkeys(selected_path_nodes))

    selected_path_edges = [_trace_to_edge(t) for t in selected_traces]
    explored_edges = [_trace_to_edge(t) for t in all_traces]
    explored_branches = [_trace_to_branch(t) for t in all_traces]

    nodes = node_repo.get_by_run(run_id)
    explored_nodes = [n.node_id for n in nodes] if nodes else []
    if not explored_nodes and all_traces:
        seen = set()
        for t in all_traces:
            seen.add(t.from_node)
            seen.add(t.to_node)
        explored_nodes = list(seen)

    gold = gold_nodes
    if not gold and run and run.metadata_:
        gold = run.metadata_.get("gold_path") or run.metadata_.get("gold_nodes")

    return GraphMetricsContext(
        run_id=run_id,
        query=query,
        answer=answer,
        selected_path_nodes=selected_path_nodes,
        selected_path_edges=selected_path_edges,
        explored_nodes=explored_nodes,
        explored_edges=explored_edges,
        explored_branches=explored_branches,
        gold_nodes=gold,
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


def _connectivity_from_nodes_edges(node_ids: List[str], edges: List[GraphEdge]) -> float:
    if not node_ids:
        return 0.0
    adj = {n: [] for n in node_ids}
    for e in edges:
        if e.from_node in adj:
            adj[e.from_node].append(e.to_node)
        if e.to_node in adj:
            adj[e.to_node].append(e.from_node)
    
    visited = set()
    max_component_size = 0
    for node_id in adj:
        if node_id not in visited:
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
    return max_component_size / len(node_ids) if node_ids else 0.0


def compute_connectivity_score(run_id: UUID, db: Session) -> float:
    """指标3: Connectivity Score"""
    node_repo = GraphNodeRepository(db)
    edge_repo = GraphEdgeRepository(db)
    nodes = node_repo.get_by_run(run_id)
    edges = edge_repo.get_by_run(run_id)
    node_ids = [n.node_id for n in nodes] if nodes else []
    graph_edges = [GraphEdge(e.from_node, e.to_node, e.relation) for e in edges]
    return _connectivity_from_nodes_edges(node_ids, graph_edges)


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


def _simple_tokenize(text: str) -> Set[str]:
    if not text:
        return set()
    t = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text.lower())
    return set(t.split()) - {"", "a", "an", "the", "is", "are", "was", "were"}


def _is_branch_irrelevant(query: Optional[str], branch: GraphBranch) -> bool:
    """规则法判断 branch 是否与 query 无关"""
    if not query or not query.strip():
        return False
    q_tokens = _simple_tokenize(query)
    b_tokens = _simple_tokenize(branch.text)
    if not q_tokens:
        return False
    overlap = q_tokens & b_tokens
    if overlap:
        return False
    if branch.relation and branch.relation.lower() in WEAK_RELATIONS:
        return True
    return True


def compute_irrelevant_branch_ratio(ctx: GraphMetricsContext) -> float:
    """无关分支比例：先用低成本规则法"""
    if not ctx.explored_branches:
        return 0.0
    irrelevant = sum(1 for b in ctx.explored_branches if _is_branch_irrelevant(ctx.query, b))
    return irrelevant / len(ctx.explored_branches)


def _rule_based_relation_chain_validity(edges: List[GraphEdge]) -> Optional[float]:
    """规则版：空 relation、重复边、断链、环路"""
    if not edges:
        return None
    if len(edges) == 1:
        return 1.0 if (edges[0].relation or "").strip() else 0.0

    seen_edges = set()
    prev_to = None
    for e in edges:
        if not (e.relation or "").strip():
            return 0.0
        key = (e.from_node, e.to_node)
        if key in seen_edges:
            return 0.0
        seen_edges.add(key)
        if prev_to is not None and e.from_node != prev_to:
            return 0.0
        prev_to = e.to_node

    visited = set()
    cur = edges[0].from_node
    for e in edges:
        if cur != e.from_node:
            return 0.0
        if cur in visited:
            return 0.0
        visited.add(cur)
        cur = e.to_node
    if cur in visited:
        return 0.0
    return 1.0


def compute_relation_chain_validity(
    ctx: GraphMetricsContext, llm_client=None
) -> Optional[float]:
    """关系链合法性：无 LLM 走规则版，有 LLM 优先 LLM"""
    if not ctx.selected_path_edges:
        return None
    if llm_client:
        try:
            path_desc = "\n".join(
                f"{e.from_node} --[{e.relation}]-> {e.to_node}"
                for e in ctx.selected_path_edges
            )
            prompt = f"""Evaluate whether this reasoning path's relation chain is logically valid.

Path:
{path_desc}

Provide a validity score (0.0 to 1.0). Return ONLY a number.
Score:"""
            response = llm_client(prompt)
            numbers = re.findall(r"0?\.\d+|[01]\.?\d*", response)
            if numbers:
                return max(0.0, min(1.0, float(numbers[0])))
        except Exception as e:
            logger.warning("LLM relation chain validity failed: %s", e)
    return _rule_based_relation_chain_validity(ctx.selected_path_edges)


def _extract_claims_rule(answer: str) -> List[str]:
    """规则版：按句拆分，过滤太短和无事实句"""
    if not answer or not answer.strip():
        return []
    sents = re.split(r"[.;。；\n]+", answer)
    claims = []
    stop = {"yes", "no", "ok", "i", "we", "it", "that", "this"}
    for s in sents:
        s = s.strip()
        if len(s) < 10:
            continue
        t = _simple_tokenize(s)
        if t and not t.issubset(stop):
            claims.append(s)
    return claims


def _build_path_evidence_text(edges: List[GraphEdge]) -> str:
    return "\n".join(f"{e.from_node} {e.relation} {e.to_node}" for e in edges)


def _is_claim_supported_rule(claim: str, evidence_text: str) -> bool:
    """规则版：关键词 overlap 或包含"""
    if not evidence_text:
        return False
    c_tok = _simple_tokenize(claim)
    e_tok = _simple_tokenize(evidence_text)
    if c_tok & e_tok:
        return True
    evidence_lower = evidence_text.lower()
    for w in c_tok:
        if len(w) > 2 and w in evidence_lower:
            return True
    return False


def compute_grounding_metrics(ctx: GraphMetricsContext) -> Optional[Dict[str, Optional[float]]]:
    """答案支撑指标：无 answer 返回 None"""
    if not ctx.answer or not ctx.answer.strip():
        return None
    claims = _extract_claims_rule(ctx.answer)
    if not claims:
        return None
    evidence = _build_path_evidence_text(ctx.selected_path_edges)
    if not ctx.selected_path_edges:
        return {
            "answer_grounded_in_path_score": 0.0,
            "unsupported_claim_ratio": 1.0,
        }
    supported = sum(1 for c in claims if _is_claim_supported_rule(c, evidence))
    total = len(claims)
    grounded = supported / total
    return {
        "answer_grounded_in_path_score": grounded,
        "unsupported_claim_ratio": 1.0 - grounded,
    }


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
    include_grounding: bool = True,
    llm_client=None
) -> Dict:
    """
    计算所有 GraphRAG 指标
    新增 grounding_metrics，irrelevant_branch_ratio，relation_chain_validity
    """
    if llm_client is None:
        try:
            from tracelens.similarity.factory import _build_llm_from_config
            llm_client = _build_llm_from_config()
        except Exception:
            pass

    ctx = build_graph_metrics_context(run_id, db, gold_path or None)
    metrics: Dict[str, Any] = {
        "structural": {},
        "quality": {},
        "semantic": {},
        "grounding": {}
    }

    path_exists = len(ctx.selected_path_edges) > 0
    metrics["structural"]["path_exists"] = path_exists
    metrics["structural"]["reasoning_hops"] = len(ctx.selected_path_edges)
    metrics["structural"]["connectivity_score"] = _connectivity_from_nodes_edges(
        ctx.explored_nodes, ctx.explored_edges
    )

    metrics["quality"]["branch_explosion_ratio"] = (
        len(ctx.explored_nodes) / len(ctx.selected_path_nodes)
        if ctx.selected_path_nodes else 0.0
    )
    metrics["quality"]["irrelevant_branch_ratio"] = compute_irrelevant_branch_ratio(ctx)

    gold = ctx.gold_nodes or gold_path
    if gold:
        selected_ids = set(ctx.selected_path_nodes)
        gold_ids = set(gold)
        metrics["quality"]["path_coverage"] = (
            len(selected_ids & gold_ids) / len(gold_ids) if gold_ids else 0.0
        )

    if include_semantic:
        metrics["semantic"]["path_relevance_score"] = compute_path_relevance_score(
            run_id, db, llm_client
        )
        metrics["semantic"]["relation_chain_validity"] = compute_relation_chain_validity(
            ctx, llm_client
        )
    else:
        metrics["semantic"]["path_relevance_score"] = None
        metrics["semantic"]["relation_chain_validity"] = None

    if include_grounding:
        gm = compute_grounding_metrics(ctx)
        metrics["grounding"] = gm if gm else {"answer_grounded_in_path_score": None, "unsupported_claim_ratio": None}
    else:
        metrics["grounding"] = {"answer_grounded_in_path_score": None, "unsupported_claim_ratio": None}

    metric_repo = MetricRepository(db)
    for name, value in metrics["structural"].items():
        v = 1.0 if value is True else (0.0 if value is False else float(value))
        metric_repo.upsert(run_id, f"graph_{name}", value=v, metadata={"type": "structural"})
    for name, value in metrics["quality"].items():
        if value is not None:
            metric_repo.upsert(run_id, f"graph_{name}", value=float(value), metadata={"type": "quality"})
    for name, value in metrics["semantic"].items():
        if value is not None:
            metric_repo.upsert(run_id, f"graph_{name}", value=float(value), metadata={"type": "semantic"})
    for name, value in metrics["grounding"].items():
        if value is not None:
            metric_repo.upsert(run_id, f"graph_{name}", value=float(value), metadata={"type": "grounding"})

    return metrics

