"""GraphRAG 指标单元测试"""
import pytest
from uuid import uuid4
from tracelens.core.graph_metrics import (
    GraphEdge,
    GraphBranch,
    GraphMetricsContext,
    compute_irrelevant_branch_ratio,
    compute_relation_chain_validity,
    compute_grounding_metrics,
    _rule_based_relation_chain_validity,
    _extract_claims_rule,
    _is_claim_supported_rule,
    _build_path_evidence_text,
)


def _ctx(**kw):
    defaults = {
        "run_id": uuid4(),
        "query": None,
        "answer": None,
        "selected_path_nodes": [],
        "selected_path_edges": [],
        "explored_nodes": [],
        "explored_edges": [],
        "explored_branches": [],
        "gold_nodes": None,
    }
    defaults.update(kw)
    return GraphMetricsContext(**defaults)


class TestIrrelevantBranchRatio:
    def test_empty_branches(self):
        ctx = _ctx(explored_branches=[], query="test")
        assert compute_irrelevant_branch_ratio(ctx) == 0.0

    def test_no_query(self):
        ctx = _ctx(
            explored_branches=[GraphBranch("A", "B", "r", 1, "A --r--> B")],
            query=None,
        )
        assert compute_irrelevant_branch_ratio(ctx) == 0.0

    def test_relevant_branch(self):
        ctx = _ctx(
            query="Alice works at Company",
            explored_branches=[
                GraphBranch("Alice", "Company", "works_at", 1, "Alice --works_at--> Company"),
            ],
        )
        assert compute_irrelevant_branch_ratio(ctx) == 0.0

    def test_weak_relation_irrelevant(self):
        ctx = _ctx(
            query="Alice",
            explored_branches=[
                GraphBranch("X", "Y", "related_to", 1, "X --related_to--> Y"),
            ],
        )
        assert compute_irrelevant_branch_ratio(ctx) >= 0.5


class TestRelationChainValidity:
    def test_empty_edges(self):
        assert _rule_based_relation_chain_validity([]) is None

    def test_single_edge_valid(self):
        assert _rule_based_relation_chain_validity([GraphEdge("A", "B", "r")]) == 1.0

    def test_single_edge_empty_relation(self):
        assert _rule_based_relation_chain_validity([GraphEdge("A", "B", "")]) == 0.0

    def test_chain_valid(self):
        edges = [
            GraphEdge("A", "B", "r1"),
            GraphEdge("B", "C", "r2"),
        ]
        assert _rule_based_relation_chain_validity(edges) == 1.0

    def test_chain_broken(self):
        edges = [
            GraphEdge("A", "B", "r1"),
            GraphEdge("X", "C", "r2"),
        ]
        assert _rule_based_relation_chain_validity(edges) == 0.0

    def test_duplicate_edge(self):
        edges = [
            GraphEdge("A", "B", "r1"),
            GraphEdge("A", "B", "r1"),
        ]
        assert _rule_based_relation_chain_validity(edges) == 0.0


class TestGroundingMetrics:
    def test_no_answer(self):
        ctx = _ctx(answer=None, selected_path_edges=[GraphEdge("A", "B", "r")])
        assert compute_grounding_metrics(ctx) is None

    def test_empty_answer(self):
        ctx = _ctx(answer="", selected_path_edges=[GraphEdge("A", "B", "r")])
        assert compute_grounding_metrics(ctx) is None

    def test_no_claims_extracted(self):
        ctx = _ctx(answer="Yes.", selected_path_edges=[GraphEdge("A", "B", "r")])
        assert compute_grounding_metrics(ctx) is None

    def test_empty_path(self):
        ctx = _ctx(
            answer="Alice works at Company_X. This is a fact.",
            selected_path_edges=[],
        )
        g = compute_grounding_metrics(ctx)
        assert g is not None
        assert g["answer_grounded_in_path_score"] == 0.0
        assert g["unsupported_claim_ratio"] == 1.0

    def test_fully_supported(self):
        ctx = _ctx(
            answer="Alice works at Company_X. Company_X located_in City_Y.",
            selected_path_edges=[
                GraphEdge("Alice", "Company_X", "works_at"),
                GraphEdge("Company_X", "City_Y", "located_in"),
            ],
        )
        g = compute_grounding_metrics(ctx)
        assert g is not None
        assert g["answer_grounded_in_path_score"] >= 0.5
        assert g["unsupported_claim_ratio"] <= 0.5


class TestClaimExtractor:
    def test_split_sentences(self):
        claims = _extract_claims_rule("First sentence. Second sentence.")
        assert len(claims) >= 1

    def test_filter_short(self):
        claims = _extract_claims_rule("Yes. No. Maybe.")
        assert len(claims) == 0


class TestEvidenceMatching:
    def test_supported_by_overlap(self):
        evidence = "Alice works_at Company_X"
        claim = "Alice works at the company"
        assert _is_claim_supported_rule(claim, evidence) is True

    def test_not_supported(self):
        evidence = "X related_to Y"
        claim = "The moon is made of cheese"
        assert _is_claim_supported_rule(claim, evidence) is False
