import logging
from uuid import UUID
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
import numpy as np
from tracelens.storage.evaluation_repository import EvaluationRepository, TestCaseRepository
from tracelens.storage.repository import RunRepository, MetricRepository
from tracelens.core.rag_metrics_simple import compute_all_metrics


def compute_evaluation_metrics(
    evaluation_id: UUID,
    db: Session,
    similarity_mode: str = "lexical",
    include_per_query: bool = False
) -> Dict[str, Any]:
    """
    计算评测任务的聚合指标
    
    Returns:
        {
            "evaluation_id": UUID,
            "version_id": str,
            "total_runs": int,
            "completed_runs": int,
            "aggregate_metrics": {
                "metric_name": {
                    "avg": float,
                    "p50": float,
                    "p95": float,
                    "min": float,
                    "max": float
                }
            },
            "per_query_metrics": [...]  # if include_per_query
        }
    """
    eval_repo = EvaluationRepository(db)
    run_repo = RunRepository(db)
    metric_repo = MetricRepository(db)
    
    evaluation = eval_repo.get(evaluation_id)
    if not evaluation:
        raise ValueError(f"Evaluation {evaluation_id} not found")
    
    # 获取所有已完成的 runs
    completed_runs = eval_repo.get_runs(evaluation_id, status="success")
    total_runs = eval_repo.get_run_count(evaluation_id)
    
    if not completed_runs:
        return {
            "evaluation_id": evaluation_id,
            "version_id": evaluation.version_id,
            "total_runs": total_runs,
            "completed_runs": 0,
            "aggregate_metrics": {},
            "per_query_metrics": [] if include_per_query else None
        }
    
    # 收集所有 run 的指标
    all_run_metrics = {}  # run_id -> {metric_name: value}
    metric_names = set()
    
    for run in completed_runs:
        # 计算该 run 的指标（如果还没计算过）
        run_metrics_dict = {}
        
        # 从数据库读取已保存的指标
        db_metrics = metric_repo.get_by_run(run.id)
        for m in db_metrics:
            if m.value is not None:
                run_metrics_dict[m.name] = m.value
                metric_names.add(m.name)
        
        # 如果数据库中没有指标，尝试计算
        if not run_metrics_dict:
            try:
                computed = compute_all_metrics(run.id, db, similarity_mode=similarity_mode)
                run_metrics_dict = {k: v for k, v in computed.items() 
                                   if k != "rank_deltas" and isinstance(v, (int, float))}
                metric_names.update(run_metrics_dict.keys())
            except Exception as e:
                logger.warning("Failed to compute metrics for run %s: %s", run.id, e)
                continue
        
        all_run_metrics[run.id] = run_metrics_dict
    
    # 计算聚合指标
    aggregate_metrics = {}
    for metric_name in metric_names:
        values = []
        for run_id, metrics in all_run_metrics.items():
            if metric_name in metrics and metrics[metric_name] is not None:
                values.append(metrics[metric_name])
        
        if values:
            aggregate_metrics[metric_name] = {
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
        "version_id": evaluation.version_id,
        "total_runs": total_runs,
        "completed_runs": len(completed_runs),
        "aggregate_metrics": aggregate_metrics,
        "per_query_metrics": per_query_metrics
    }


def compute_evaluation_comparison(
    eval_a_id: UUID,
    eval_b_id: UUID,
    db: Session,
    similarity_mode: str = "lexical",
    include_per_query: bool = False
) -> Dict[str, Any]:
    """
    对比两个评测任务的指标
    
    Returns:
        {
            "evaluation_a": {"id": ..., "version_id": ..., "name": ...},
            "evaluation_b": {"id": ..., "version_id": ..., "name": ...},
            "metrics_delta": {
                "metric_name": {
                    "avg_a": float,
                    "avg_b": float,
                    "delta": float,
                    "percent_change": float
                }
            },
            "per_query_comparison": [...]  # if include_per_query
        }
    """
    eval_repo = EvaluationRepository(db)
    test_case_repo = TestCaseRepository(db)
    
    evaluation_a = eval_repo.get(eval_a_id)
    evaluation_b = eval_repo.get(eval_b_id)
    
    if not evaluation_a or not evaluation_b:
        raise ValueError("One or both evaluations not found")
    
    # 确保两个评测使用同一个 test_suite
    if evaluation_a.test_suite_id != evaluation_b.test_suite_id:
        raise ValueError("Evaluations must use the same test suite for comparison")
    
    # 获取两个评测的指标
    metrics_a = compute_evaluation_metrics(eval_a_id, db, similarity_mode, include_per_query=True)
    metrics_b = compute_evaluation_metrics(eval_b_id, db, similarity_mode, include_per_query=True)
    
    # 计算聚合指标的差异
    metrics_delta = {}
    all_metric_names = set(metrics_a["aggregate_metrics"].keys()) | set(metrics_b["aggregate_metrics"].keys())
    
    for metric_name in all_metric_names:
        stats_a = metrics_a["aggregate_metrics"].get(metric_name, {})
        stats_b = metrics_b["aggregate_metrics"].get(metric_name, {})
        
        avg_a = stats_a.get("avg")
        avg_b = stats_b.get("avg")
        
        if avg_a is not None and avg_b is not None:
            delta = avg_b - avg_a
            percent_change = (delta / avg_a * 100) if avg_a != 0 else None
            
            metrics_delta[metric_name] = {
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
            
            # 计算指标差异
            metrics_delta_per_query = {}
            metric_names_per_query = set()
            if item_a:
                metric_names_per_query.update(item_a["metrics"].keys())
            if item_b:
                metric_names_per_query.update(item_b["metrics"].keys())
            
            for metric_name in metric_names_per_query:
                value_a = item_a["metrics"].get(metric_name) if item_a else None
                value_b = item_b["metrics"].get(metric_name) if item_b else None
                
                delta = None
                percent_change = None
                if value_a is not None and value_b is not None:
                    delta = value_b - value_a
                    percent_change = (delta / value_a * 100) if value_a != 0 else None
                
                metrics_delta_per_query[metric_name] = {
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

