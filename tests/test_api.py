"""
API integration tests - covers all major endpoints.
Run: python3 tests/test_api.py (from project root)
Uses TestClient (in-process) for reliable testing against latest code.
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

_results = []


_client = None


def _get_client():
    global _client
    if _client is None:
        from fastapi.testclient import TestClient
        from tracelens.main import app
        _client = TestClient(app)
    return _client


def req(method, path, body=None, params=None, base=None):
    client = _get_client()
    url = "/health" if path == "/health" else f"/api/v1{path}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    if method == "GET":
        r = client.get(url)
    else:
        r = client.request(method, url, json=body)
    return r.status_code, r.json() if r.content else {}


def check(name, fn):
    try:
        fn()
        print(f"  {PASS}  {name}")
        _results.append((name, True, None))
    except Exception as e:
        print(f"  {FAIL}  {name}  ({e})")
        _results.append((name, False, str(e)))


# ── state shared across tests ──────────────────────────────────────────────────
state = {}


# ══════════════════════════════════════════════════════════════════════════════
print("\n[Health]")

def t_health():
    s, b = req("GET", "/health")
    assert s == 200 and b["status"] == "ok"

check("GET /health", t_health)


# ══════════════════════════════════════════════════════════════════════════════
print("\n[Run lifecycle]")

def t_run_start():
    s, b = req("POST", "/run/start", {"name": "test-run-1"})
    assert s == 200 and "id" in b
    state["run_id"] = b["id"]

def t_run_end():
    s, b = req("POST", f"/run/{state['run_id']}/end", {"status": "completed"})
    assert s == 200 and b["status"] == "completed"

check("POST /run/start", t_run_start)
check("POST /run/{id}/end", t_run_end)


# ══════════════════════════════════════════════════════════════════════════════
print("\n[Span lifecycle]")

def t_span_setup():
    # need an open run
    s, b = req("POST", "/run/start", {"name": "span-test-run"})
    assert s == 200
    state["span_run_id"] = b["id"]

def t_span_start():
    s, b = req("POST", "/span/start", {
        "run_id": state["span_run_id"],
        "name": "retrieval-span",
        "input": {"query": "what is RAG?"}
    })
    assert s == 200 and "id" in b
    state["span_id"] = b["id"]

def t_span_end():
    s, b = req("POST", f"/span/{state['span_id']}/end",
               {"output": {"chunks": ["chunk1", "chunk2"]}})
    assert s == 200

check("setup span run", t_span_setup)
check("POST /span/start", t_span_start)
check("POST /span/{id}/end", t_span_end)


# ══════════════════════════════════════════════════════════════════════════════
print("\n[Event & Metric]")

def t_event():
    s, b = req("POST", "/event", {
        "run_id": state["span_run_id"],
        "name": "retrieval_completed",
        "data": {"chunk_count": 5}
    })
    assert s == 200 and "id" in b

def t_metric():
    s, b = req("POST", "/metric", {
        "run_id": state["span_run_id"],
        "name": "latency_ms",
        "value": 123.4
    })
    assert s == 200 and "id" in b

check("POST /event", t_event)
check("POST /metric", t_metric)


# ══════════════════════════════════════════════════════════════════════════════
print("\n[Ingest]")

def t_ingest_langsmith():
    s, b = req("POST", "/ingest/langsmith", {"name": "ingest-test", "child_runs": []})
    assert s == 200 and "run_id" in b

def t_ingest_langfuse():
    s, b = req("POST", "/ingest/langfuse", {"name": "ingest-test", "observations": []})
    assert s == 200 and "run_id" in b

check("POST /ingest/langsmith", t_ingest_langsmith)
check("POST /ingest/langfuse", t_ingest_langfuse)


# ══════════════════════════════════════════════════════════════════════════════
print("\n[RAG pipeline]")

def t_rag_setup():
    s, b = req("POST", "/run/start", {"name": "rag-pipeline-run"})
    assert s == 200
    state["rag_run_id"] = b["id"]

def t_retrieval_completed():
    s, b = req("POST", "/retrieval/completed", {
        "run_id": state["rag_run_id"],
        "query": "what is machine learning?",
        "retrieved_chunks": [
            {"chunk_id": "c1", "content": "Machine learning is a subset of AI.", "score": 0.95},
            {"chunk_id": "c2", "content": "Deep learning uses neural networks.", "score": 0.87},
            {"chunk_id": "c3", "content": "Supervised learning uses labeled data.", "score": 0.80},
        ]
    })
    assert s == 200 and b["status"] == "ok"

def t_prompt_built():
    s, b = req("POST", "/prompt/built", {
        "run_id": state["rag_run_id"],
        "prompt_chunks": ["c1", "c2"]
    })
    assert s == 200 and b["status"] == "ok"

def t_answer_generated():
    s, b = req("POST", "/answer/generated", {
        "run_id": state["rag_run_id"],
        "answer": "Machine learning is a subset of AI that enables computers to learn from data."
    })
    assert s == 200 and b["status"] == "ok"

def t_gold_chunks():
    s, b = req("POST", "/gold/chunks", {
        "run_id": state["rag_run_id"],
        "gold_chunk_ids": ["c1", "c2"]
    })
    assert s == 200 and b["status"] == "ok"

def t_run_finished():
    s, b = req("POST", "/run/finished", {
        "run_id": state["rag_run_id"],
        "status": "completed"
    })
    assert s == 200 and b["status"] == "ok"

def t_rag_metrics():
    s, b = req("GET", f"/run/{state['rag_run_id']}/metrics")
    assert s == 200 and "run_id" in b and "metrics" in b

check("setup rag run", t_rag_setup)
check("POST /retrieval/completed", t_retrieval_completed)
check("POST /prompt/built", t_prompt_built)
check("POST /answer/generated", t_answer_generated)
check("POST /gold/chunks", t_gold_chunks)
check("POST /run/finished", t_run_finished)
check("GET /run/{id}/metrics", t_rag_metrics)


# ══════════════════════════════════════════════════════════════════════════════
print("\n[RAG metrics (legacy) & diff]")

def t_rag_metrics_legacy():
    s, b = req("GET", f"/run/{state['rag_run_id']}/rag-metrics")
    assert s == 200

def t_run_graph():
    s, b = req("GET", f"/run/{state['rag_run_id']}/graph")
    assert s == 200

def t_chunk_attribution():
    s, b = req("GET", f"/run/{state['rag_run_id']}/chunk-attribution")
    assert s == 200 and "attributions" in b

def t_retrieval_diff():
    # create a second rag run for diff
    _, b = req("POST", "/run/start", {"name": "rag-run-v2"})
    run2 = b["id"]
    state["rag_run_id_v2"] = run2
    req("POST", "/retrieval/completed", {
        "run_id": run2,
        "query": "what is machine learning?",
        "retrieved_chunks": [
            {"chunk_id": "c1", "content": "Machine learning is a subset of AI.", "score": 0.90},
            {"chunk_id": "c3", "content": "Supervised learning uses labeled data.", "score": 0.85},
        ]
    })
    req("POST", "/run/finished", {"run_id": run2, "status": "completed"})
    s, b = req("GET", f"/run/{run2}/retrieval_diff",
               params={"prev_run_id": state["rag_run_id"]})
    assert s == 200 and "new_chunks_ratio" in b

def t_runs_diff():
    s, b = req("GET", "/runs/diff",
               params={"run_id_a": state["rag_run_id"], "run_id_b": state["rag_run_id_v2"]})
    assert s == 200 and "metrics_diff" in b

check("GET /run/{id}/rag-metrics", t_rag_metrics_legacy)
check("GET /run/{id}/graph", t_run_graph)
check("GET /run/{id}/chunk-attribution", t_chunk_attribution)
check("GET /run/{id}/retrieval_diff", t_retrieval_diff)
check("GET /runs/diff", t_runs_diff)


# ══════════════════════════════════════════════════════════════════════════════
print("\n[GraphRAG]")

def t_graph_setup():
    s, b = req("POST", "/run/start", {"name": "graph-run-1"})
    assert s == 200
    state["graph_run_id"] = b["id"]

def t_graph_expand():
    for step, (fn, tn, rel) in enumerate([
        ("AI", "MachineLearning", "includes"),
        ("MachineLearning", "DeepLearning", "includes"),
        ("DeepLearning", "NeuralNetwork", "uses"),
    ]):
        s, b = req("POST", "/graph/expand", {
            "run_id": state["graph_run_id"],
            "from_node": fn, "to_node": tn,
            "relation": rel, "step_index": step
        })
        assert s == 200 and b["status"] == "ok"

def t_path_selected():
    s, b = req("POST", "/graph/path/selected", {
        "run_id": state["graph_run_id"],
        "path": ["AI", "MachineLearning", "DeepLearning"]
    })
    assert s == 200 and b["status"] == "ok"

def t_graph_metrics():
    s, b = req("GET", f"/run/{state['graph_run_id']}/graph-metrics")
    assert s == 200 and "structural_metrics" in b

def t_reasoning_path():
    s, b = req("GET", f"/run/{state['graph_run_id']}/reasoning-path")
    assert s == 200 and "selected_path" in b

check("setup graph run", t_graph_setup)
check("POST /graph/expand", t_graph_expand)
check("POST /graph/path/selected", t_path_selected)
check("GET /run/{id}/graph-metrics", t_graph_metrics)
check("GET /run/{id}/reasoning-path", t_reasoning_path)


# ══════════════════════════════════════════════════════════════════════════════
print("\n[Evaluation]")

def t_create_suite():
    s, b = req("POST", "/test_suite", {"name": "suite-1", "description": "smoke test suite"})
    assert s == 200 and "id" in b
    state["suite_id"] = b["id"]

def t_get_suite():
    s, b = req("GET", f"/test_suite/{state['suite_id']}")
    assert s == 200 and b["name"] == "suite-1"

def t_bulk_test_cases():
    s, b = req("POST", f"/test_suite/{state['suite_id']}/test_cases", {
        "test_cases": [
            {"query": "What is RAG?", "gold_answer": "RAG is retrieval augmented generation.",
             "gold_chunk_ids": ["c1"]},
            {"query": "What is a neural network?", "gold_answer": "Neural networks are computing systems.",
             "gold_chunk_ids": ["c2"]},
        ]
    })
    assert s == 200 and b["created_count"] == 2

def t_get_test_cases():
    s, b = req("GET", f"/test_suite/{state['suite_id']}/test_cases")
    assert s == 200 and len(b) == 2

def t_create_evaluation():
    s, b = req("POST", "/evaluation", {
        "name": "eval-1",
        "test_suite_id": state["suite_id"],
        "version_id": "v1.0"
    })
    assert s == 200 and "id" in b
    state["eval_id"] = b["id"]

def t_get_evaluation():
    s, b = req("GET", f"/evaluation/{state['eval_id']}")
    assert s == 200 and b["name"] == "eval-1"

def t_eval_status():
    s, b = req("GET", f"/evaluation/{state['eval_id']}/status")
    assert s == 200 and "status" in b

def t_eval_test_cases():
    s, b = req("GET", f"/evaluation/{state['eval_id']}/test_cases")
    assert s == 200 and isinstance(b, list)

def t_eval_compute():
    s, b = req("POST", f"/evaluation/{state['eval_id']}/compute")
    assert s == 200 and b.get("status") == "accepted"

def t_eval_metrics():
    s, b = req("GET", f"/evaluation/{state['eval_id']}/metrics")
    assert s == 200 and "aggregate_metrics" in b

def t_create_eval2():
    s, b = req("POST", "/evaluation", {
        "name": "eval-2",
        "test_suite_id": state["suite_id"],
        "version_id": "v2.0"
    })
    assert s == 200 and "id" in b
    state["eval_id_2"] = b["id"]

def t_eval_compare():
    s, b = req("GET", "/evaluation/compare",
               params={"eval_a": state["eval_id"], "eval_b": state["eval_id_2"]})
    assert s == 200 and "metrics_delta" in b

def t_eval_graph_metrics():
    s, b = req("GET", f"/evaluation/{state['eval_id']}/graph_metrics")
    assert s == 200 and "aggregate_metrics" in b

def t_eval_graph_compare():
    s, b = req("GET", "/evaluation/graph_compare",
               params={"eval_a": state["eval_id"], "eval_b": state["eval_id_2"]})
    assert s == 200 and "metrics_delta" in b

check("POST /test_suite", t_create_suite)
check("GET /test_suite/{id}", t_get_suite)
check("POST /test_suite/{id}/test_cases", t_bulk_test_cases)
check("GET /test_suite/{id}/test_cases", t_get_test_cases)
check("POST /evaluation", t_create_evaluation)
check("GET /evaluation/{id}", t_get_evaluation)
check("GET /evaluation/{id}/status", t_eval_status)
check("GET /evaluation/{id}/test_cases", t_eval_test_cases)
check("POST /evaluation/{id}/compute", t_eval_compute)
check("GET /evaluation/{id}/metrics", t_eval_metrics)
check("POST /evaluation (eval-2)", t_create_eval2)
check("GET /evaluation/compare", t_eval_compare)
check("GET /evaluation/{id}/graph_metrics", t_eval_graph_metrics)
check("GET /evaluation/graph_compare", t_eval_graph_compare)


# ══════════════════════════════════════════════════════════════════════════════
print("\n[404 guard]")

def t_404_run():
    s, _ = req("GET", "/run/00000000-0000-0000-0000-000000000000/metrics")
    assert s == 404

def t_404_suite():
    s, _ = req("GET", "/test_suite/00000000-0000-0000-0000-000000000000")
    assert s == 404

check("404 on missing run", t_404_run)
check("404 on missing test_suite", t_404_suite)


# ══════════════════════════════════════════════════════════════════════════════
total = len(_results)
passed = sum(1 for _, ok, _ in _results if ok)
failed = total - passed

print(f"\n{'='*55}")
print(f"  Result: {passed}/{total} passed", end="")
if failed:
    print(f"  ({failed} failed)")
    for name, ok, err in _results:
        if not ok:
            print(f"    - {name}: {err}")
else:
    print("  — all green")
print('='*55)

sys.exit(0 if failed == 0 else 1)
