"""
TraceLens 评测对比示例
专注于版本对比场景，包含 per-query 详细对比
"""
import sys
sys.path.insert(0, "..")

from uuid import UUID
from sdk.evaluation_client import EvaluationClient


def main():
    BASE_URL = "http://localhost:8000"
    eval_client = EvaluationClient(BASE_URL)
    
    print("=" * 60)
    print("TraceLens 评测对比示例")
    print("=" * 60)
    
    # 假设已经运行了两个评测任务
    # 在实际场景中，这些 ID 来自之前的评测
    print("\n请输入两个评测任务的 ID（用于对比）:")
    eval_a_id_str = input("评测任务 A (v1.0) ID: ").strip()
    eval_b_id_str = input("评测任务 B (v2.0) ID: ").strip()
    
    if not eval_a_id_str or not eval_b_id_str:
        print("使用示例 ID（请替换为实际 ID）")
        # 这里使用占位符，实际运行时需要替换
        print("错误：请提供有效的评测任务 ID")
        return
    
    eval_a_id = UUID(eval_a_id_str)
    eval_b_id = UUID(eval_b_id_str)
    
    # ========== 获取评测详情 ==========
    print("\n[Step 1] 获取评测详情...")
    
    eval_a = eval_client.get_evaluation(eval_a_id)
    eval_b = eval_client.get_evaluation(eval_b_id)
    
    print(f"✓ 评测 A: {eval_a['name']} (version: {eval_a['version_id']})")
    print(f"  - 完成: {eval_a['completed_runs']}/{eval_a['total_runs']}")
    print(f"✓ 评测 B: {eval_b['name']} (version: {eval_b['version_id']})")
    print(f"  - 完成: {eval_b['completed_runs']}/{eval_b['total_runs']}")
    
    # ========== 聚合指标对比 ==========
    print("\n[Step 2] 聚合指标对比...")
    
    comparison = eval_client.compare_evaluations(
        eval_a_id=eval_a_id,
        eval_b_id=eval_b_id,
        similarity_mode="lexical",
        include_per_query=False
    )
    
    print(f"\n版本对比: {comparison['evaluation_a']['version_id']} → {comparison['evaluation_b']['version_id']}")
    print("\n指标变化（平均值）:")
    print("-" * 60)
    
    for metric_name, delta_stats in comparison["metrics_delta"].items():
        avg_a = delta_stats.get("avg_a")
        avg_b = delta_stats.get("avg_b")
        delta = delta_stats.get("delta")
        percent_change = delta_stats.get("percent_change")
        
        if delta is not None and percent_change is not None:
            direction = "↑" if delta > 0 else "↓" if delta < 0 else "="
            color = "+" if delta > 0 else "" if delta < 0 else " "
            print(f"{metric_name:40} | {avg_a:8.4f} → {avg_b:8.4f} | {direction} {color}{percent_change:6.2f}%")
    
    # ========== Per-Query 详细对比 ==========
    print("\n[Step 3] Per-Query 详细对比...")
    
    comparison_detailed = eval_client.compare_evaluations(
        eval_a_id=eval_a_id,
        eval_b_id=eval_b_id,
        similarity_mode="lexical",
        include_per_query=True
    )
    
    if comparison_detailed.get("per_query_comparison"):
        print(f"\n共 {len(comparison_detailed['per_query_comparison'])} 个问题的详细对比:")
        print("-" * 60)
        
        for idx, item in enumerate(comparison_detailed["per_query_comparison"][:5]):  # 只显示前5个
            print(f"\n[{idx+1}] Query: {item['query'][:60]}...")
            print(f"    Run A: {item['run_id_a']}")
            print(f"    Run B: {item['run_id_b']}")
            
            # 选择几个关键指标显示
            key_metrics = ["topK_chunk_query_similarity", "prompt_chunk_answer_similarity", "exact_recall_vs_gold_chunks"]
            
            for metric_name in key_metrics:
                if metric_name in item["metrics_delta"]:
                    delta_info = item["metrics_delta"][metric_name]
                    value_a = delta_info.get("value_a")
                    value_b = delta_info.get("value_b")
                    delta = delta_info.get("delta")
                    
                    if value_a is not None and value_b is not None and delta is not None:
                        direction = "↑" if delta > 0 else "↓" if delta < 0 else "="
                        print(f"    - {metric_name:35}: {value_a:.4f} → {value_b:.4f} ({direction} {delta:+.4f})")
        
        if len(comparison_detailed["per_query_comparison"]) > 5:
            print(f"\n... 还有 {len(comparison_detailed['per_query_comparison']) - 5} 个问题未显示")
    else:
        print("未生成 per-query 对比（请确保两个评测使用同一测试集）")
    
    # ========== 总结 ==========
    print("\n" + "=" * 60)
    print("对比分析总结")
    print("=" * 60)
    
    # 分析指标变化趋势
    improved_count = 0
    degraded_count = 0
    unchanged_count = 0
    
    for metric_name, delta_stats in comparison["metrics_delta"].items():
        delta = delta_stats.get("delta")
        if delta is not None:
            if delta > 0.01:  # 阈值
                improved_count += 1
            elif delta < -0.01:
                degraded_count += 1
            else:
                unchanged_count += 1
    
    print(f"\n指标变化统计:")
    print(f"  改进: {improved_count} 个指标")
    print(f"  下降: {degraded_count} 个指标")
    print(f"  持平: {unchanged_count} 个指标")
    
    if improved_count > degraded_count:
        print(f"\n✓ 版本 {comparison['evaluation_b']['version_id']} 整体优于版本 {comparison['evaluation_a']['version_id']}")
    elif degraded_count > improved_count:
        print(f"\n✗ 版本 {comparison['evaluation_b']['version_id']} 整体劣于版本 {comparison['evaluation_a']['version_id']}")
    else:
        print(f"\n= 两个版本表现接近")
    
    print("\n建议:")
    print("- 关注 p95 指标，识别异常值和边缘情况")
    print("- 查看 per-query 对比，找出哪些问题被改进或恶化")
    print("- 结合业务场景，权衡不同指标的重要性")


if __name__ == "__main__":
    main()

