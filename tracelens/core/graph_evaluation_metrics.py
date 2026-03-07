"""
GraphRAG 批量评测指标计算
专注于推理路径质量的聚合分析和版本对比
"""
import logging
from uuid import UUID

logger = logging.getLogger(__name__)
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import numpy as np
from tracelens.storage.evaluation_repository import EvaluationRepository, TestCaseRepository
from tracelens.storage.repository import RunRepository, MetricRepository
from tracelens.core.graph_metrics import compute_all_graph_metrics


def compute_graph_evaluation_metrics(
    evaluation_id: UUID,
    db: Session,
    include_semantic: bool = False,
    include_per_query: bool = False,
    llm_client=None
) -> Dict[str, Any]:
    """
    计算 GraphRAG 评测任务的聚合指标
    
    Args:
        evaluation_id: 评测任务 ID
        db: 数据库会话
        include_semantic: 是否包含语义指标（LLM Judge）
        include_per_query: 是否包含每个问题的详细指标
        llm_client: LLM 客户端（如果需要计算语义指标）
    
    Returns:
        {
            "evaluation_id": UUID,
            "name": str,
            "version_id": str,
            "total_runs": int,
            "completed_runs": int,
            "status": str,
            "aggregate_metrics": {
                "structural": {
                    "path_exists_rate": {"avg": 0.95, "p50": 1.0, "p95": 1.0},
                    "avg_reasoning_hops": {"avg": 3.2, "p50": 3.0, "p95": 5.0},
                    "avg_connectivity_score": {"avg": 0.75, "p50": 0.80, "p95": 0.95}
                },
                "quality": {
                    "avg_branch_explosion_ratio": {"avg": 8.5, "p50": 7.0, "p95": 15.0},
                    "avg_path_coverage": {"avg": 0.72, "p50": 0.75, "p95": 0.90}  # 如果有 gold_path
                },
                "semantic": {
                    "avg_path_relevance_score": {"avg": 0.78, "p50": 0.80, "p95": 0.90}  # 如果 include_semantic
                }
            },
            "per_query_metrics": [...]  # if include_per_query
        }
    """
    eval_repo = EvaluationRepository(db)
    run_repo = RunRepository(db)
    metric_repo = MetricRepository(db)
    test_case_repo = TestCaseRepository(db)
    
    evaluation = eval_repo.get(evaluation_id)
    if not evaluation:
        raise ValueError(f"Evaluation {evaluation_id} not found")
    
    # 获取所有已完成的 runs
    completed_runs = eval_repo.get_runs(evaluation_id, status="success")
    total_runs = eval_repo.get_run_count(evaluation_id)
    
    if not completed_runs:
        return {
            "evaluation_id": evaluation_id,
            "name": evaluation.name,
            "version_id": evaluation.version_id,
            "total_runs": total_runs,
            "completed_runs": 0,
            "status": evaluation.status,
            "aggregate_metrics": {
                "structural": {},
                "quality": {},
                "semantic": {}
            },
            "per_query_metrics": [] if include_per_query else None
        }
    
    # 收集所有 run 的指标
    all_run_metrics = {}  # run_id -> {category: {metric_name: value}}
    
    for run in completed_runs:
        # 从数据库读取已保存的指标
        db_metrics = metric_repo.get_by_run(run.id)
        
        run_metrics = {
            "structural": {},
            "quality": {},
            "semantic": {}
        }
        
        # 如果数据库中有 GraphRAG 指标，直接使用
        has_graph_metrics = False
        for m in db_metrics:
            if m.name.startswith("graph_") and m.value is not None:
                has_graph_metrics = True
                category = m.metadata_.get("type", "quality")
                metric_name = m.name.replace("graph_", "")
                run_metrics[category][metric_name] = m.value
        
        # 如果没有，尝试计算
        if not has_graph_metrics:
            try:
                # 获取 gold_path（如果有）
                gold_path = None
                if run.test_case_id:
                    test_case = test_case_repo.get(run.test_case_id)
                    if test_case and test_case.gold_path:
                        gold_path = test_case.gold_path
                
                # 或者从 run.metadata 中获取
                if not gold_path and run.metadata_:
                    gold_path = run.metadata_.get("gold_path")
                
                # 计算 GraphRAG 指标
                computed = compute_all_graph_metrics(
                    run.id, db, 
                    gold_path=gold_path,
                    include_semantic=include_semantic,
                    llm_client=llm_client
                )
                
                run_metrics = computed
            except Exception as e:
                logger.warning("Failed to compute graph metrics for run %s: %s", run.id, e)
                continue
        
        all_run_metrics[run.id] = run_metrics
    
    # 计算聚合指标
    aggregate_metrics = {
        "structural": {},
        "quality": {},
        "semantic": {}
    }
    
    # 聚合每个类别的指标
    for category in ["structural", "quality", "semantic"]:
        # 收集所有指标名称
        metric_names = set()
        for run_id, metrics in all_run_metrics.items():
            metric_names.update(metrics.get(category, {}).keys())
        
        # 对每个指标计算聚合统计
        for metric_name in metric_names:
            values = []
            for run_id, metrics in all_run_metrics.items():
                value = metrics.get(category, {}).get(metric_name)
                if value is not None:
                    # bool 转 float
                    if isinstance(value, bool):
                        value = 1.0 if value else 0.0
                    values.append(value)
            
            if values:
                aggregate_metrics[category][metric_name] = {
                    "avg": float(np.mean(values)),
                    "p50": float(np.percentile(values, 50)),
                    "p95": float(np.percentile(values, 95)),
                    "min": float(np.min(values)),
                    "max": float(np.max(values))
                }
    
    # 构建 per-query metrics（如果需要）
    per_query_metrics = None
    if include_per_query:
        per_query_metrics = []
        for run in completed_runs:
            if run.id in all_run_metrics:
                per_query_metrics.append({
                    "test_case_id": run.test_case_id,
                    "query": run.query,
                    "run_id": run.id,
                    "metrics": all_run_metrics[run.id]
                })
    
    return {
        "evaluation_id": evaluation_id,
        "name": evaluation.name,
        "version_id": evaluation.version_id,
        "total_runs": total_runs,
        "completed_runs": len(completed_runs),
        "status": evaluation.status,
        "aggregate_metrics": aggregate_metrics,
        "per_query_metrics": per_query_metrics
    }


def compute_graph_evaluation_comparison(
    eval_a_id: UUID,
    eval_b_id: UUID,
    db: Session,
    include_semantic: bool = False,
    include_per_query: bool = False,
    llm_client=None
) -> Dict[str, Any]:
    """
    对比两个 GraphRAG 评测任务
    
    Args:
        eval_a_id: 评测任务 A ID
        eval_b_id: 评测任务 B ID
        db: 数据库会话
        include_semantic: 是否包含语义指标
        include_per_query: 是否包含每个问题的详细对比
        llm_client: LLM 客户端
    
    Returns:
        {
            "evaluation_a": {"id": ..., "version_id": "v1.0_BFS", "name": ...},
            "evaluation_b": {"id": ..., "version_id": "v2.0_BeamSearch", "name": ...},
            "metrics_delta": {
                "structural": {
                    "avg_reasoning_hops": {
                        "avg_a": 4.5, "avg_b": 3.2,
                        "delta": -1.3, "percent_change": -28.9
                    }
                },
                "quality": {
                    "avg_branch_explosion_ratio": {
                        "avg_a": 15.2, "avg_b": 8.5,
                        "delta": -6.7, "percent_change": -44.1
                    }
                }
            },
            "per_query_comparison": [...]  # if include_per_query
        }
    """
    eval_repo = EvaluationRepository(db)
    
    evaluation_a = eval_repo.get(eval_a_id)
    evaluation_b = eval_repo.get(eval_b_id)
    
    if not evaluation_a or not evaluation_b:
        raise ValueError("One or both evaluations not found")
    
    # 确保两个评测使用同一个 test_suite
    if evaluation_a.test_suite_id != evaluation_b.test_suite_id:
        raise ValueError("Evaluations must use the same test suite for comparison")
    
    # 获取两个评测的指标
    metrics_a = compute_graph_evaluation_metrics(
        eval_a_id, db, 
        include_semantic=include_semantic,
        include_per_query=True,
        llm_client=llm_client
    )
    metrics_b = compute_graph_evaluation_metrics(
        eval_b_id, db,
        include_semantic=include_semantic,
        include_per_query=True,
        llm_client=llm_client
    )
    
    # 计算聚合指标的差异
    metrics_delta = {
        "structural": {},
        "quality": {},
        "semantic": {}
    }
    
    for category in ["structural", "quality", "semantic"]:
        agg_a = metrics_a["aggregate_metrics"].get(category, {})
        agg_b = metrics_b["aggregate_metrics"].get(category, {})
        
        all_metric_names = set(agg_a.keys()) | set(agg_b.keys())
        
        for metric_name in all_metric_names:
            stats_a = agg_a.get(metric_name, {})
            stats_b = agg_b.get(metric_name, {})
            
            avg_a = stats_a.get("avg")
            avg_b = stats_b.get("avg")
            
            if avg_a is not None and avg_b is not None:
                delta = avg_b - avg_a
                percent_change = (delta / avg_a * 100) if avg_a != 0 else None
                
                metrics_delta[category][metric_name] = {
                    "avg_a": avg_a,
                    "avg_b": avg_b,
                    "delta": delta,
                    "percent_change": percent_change,
                    "p50_a": stats_a.get("p50"),
                    "p50_b": stats_b.get("p50"),
                    "p95_a": stats_a.get("p95"),
                    "p95_b": stats_b.get("p95")
                }
    
    # 计算 per-query 对比（如果需要）
    per_query_comparison = None
    if include_per_query and metrics_a["per_query_metrics"] and metrics_b["per_query_metrics"]:
        # 按 test_case_id 对齐
        per_query_a = {item["test_case_id"]: item for item in metrics_a["per_query_metrics"]}
        per_query_b = {item["test_case_id"]: item for item in metrics_b["per_query_metrics"]}
        
        per_query_comparison = []
        all_test_case_ids = set(per_query_a.keys()) | set(per_query_b.keys())
        
        for test_case_id in all_test_case_ids:
            item_a = per_query_a.get(test_case_id)
            item_b = per_query_b.get(test_case_id)
            
            # 获取 query（从任一侧）
            query = (item_a or item_b)["query"]
            
            # 计算指标差异（按类别）
            metrics_delta_per_query = {
                "structural": {},
                "quality": {},
                "semantic": {}
            }
            
            for category in ["structural", "quality", "semantic"]:
                metrics_a_cat = item_a["metrics"].get(category, {}) if item_a else {}
                metrics_b_cat = item_b["metrics"].get(category, {}) if item_b else {}
                
                all_metric_names_cat = set(metrics_a_cat.keys()) | set(metrics_b_cat.keys())
                
                for metric_name in all_metric_names_cat:
                    value_a = metrics_a_cat.get(metric_name)
                    value_b = metrics_b_cat.get(metric_name)
                    
                    delta = None
                    percent_change = None
                    if value_a is not None and value_b is not None:
                        # bool 转 float
                        if isinstance(value_a, bool):
                            value_a = 1.0 if value_a else 0.0
                        if isinstance(value_b, bool):
                            value_b = 1.0 if value_b else 0.0
                        
                        delta = value_b - value_a
                        percent_change = (delta / value_a * 100) if value_a != 0 else None
                    
                    metrics_delta_per_query[category][metric_name] = {
                        "value_a": value_a,
                        "value_b": value_b,
                        "delta": delta,
                        "percent_change": percent_change
                    }
            
            per_query_comparison.append({
                "test_case_id": test_case_id,
                "query": query,
                "run_id_a": item_a["run_id"] if item_a else None,
                "run_id_b": item_b["run_id"] if item_b else None,
                "metrics_delta": metrics_delta_per_query
            })
    
    return {
        "evaluation_a": {
            "id": evaluation_a.id,
            "version_id": evaluation_a.version_id,
            "name": evaluation_a.name
        },
        "evaluation_b": {
            "id": evaluation_b.id,
            "version_id": evaluation_b.version_id,
            "name": evaluation_b.name
        },
        "metrics_delta": metrics_delta,
        "per_query_comparison": per_query_comparison
    }

