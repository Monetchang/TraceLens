"""
GraphRAG 评测对比示例
专注于剪枝策略优化效果分析
"""
from uuid import UUID
from sdk.evaluation_client import EvaluationClient


def main():
    """
    假设你已经运行了两个评测任务：
    - evaluation_v1_id: 使用 BFS 策略
    - evaluation_v2_id: 使用 Beam Search 策略
    
    本示例演示如何深入分析两个版本的差异
    """
    eval_client = EvaluationClient(base_url="http://localhost:8000")
    
    # 替换为你实际的评测任务 ID
    evaluation_v1_id = UUID("your-eval-v1-id-here")
    evaluation_v2_id = UUID("your-eval-v2-id-here")
    
    # 获取详细对比数据（包含 per-query）
    print("=== 获取详细对比数据 ===")
    comparison = eval_client.compare_graph_evaluations(
        eval_a_id=evaluation_v1_id,
        eval_b_id=evaluation_v2_id,
        include_per_query=True
    )
    
    print(f"\n版本 A: {comparison['evaluation_a']['version_id']}")
    print(f"版本 B: {comparison['evaluation_b']['version_id']}")
    
    # 1. 整体指标对比
    print("\n" + "="*60)
    print("整体指标对比")
    print("="*60)
    
    # 分支爆炸比
    if "quality" in comparison["metrics_delta"]:
        if "branch_explosion_ratio" in comparison["metrics_delta"]["quality"]:
            branch = comparison["metrics_delta"]["quality"]["branch_explosion_ratio"]
            print(f"\n📊 分支爆炸比:")
            print(f"  v1.0 (BFS)       : {branch['avg_a']:.2f} (p50: {branch.get('p50_a', 0):.2f}, p95: {branch.get('p95_a', 0):.2f})")
            print(f"  v2.0 (Beam)      : {branch['avg_b']:.2f} (p50: {branch.get('p50_b', 0):.2f}, p95: {branch.get('p95_b', 0):.2f})")
            print(f"  变化             : {branch['delta']:.2f} ({branch['percent_change']:.1f}%)")
            
            if branch['delta'] < -5.0:
                print(f"  ✅ 显著改善：剪枝效率大幅提升")
            elif branch['delta'] < 0:
                print(f"  ✅ 小幅改善")
            else:
                print(f"  ⚠️  退化：需要检查剪枝策略")
    
    # 推理跳数
    if "structural" in comparison["metrics_delta"]:
        if "reasoning_hops" in comparison["metrics_delta"]["structural"]:
            hops = comparison["metrics_delta"]["structural"]["reasoning_hops"]
            print(f"\n📊 推理跳数:")
            print(f"  v1.0 (BFS)       : {hops['avg_a']:.2f} 跳")
            print(f"  v2.0 (Beam)      : {hops['avg_b']:.2f} 跳")
            print(f"  变化             : {hops['delta']:.2f} 跳")
    
    # 路径覆盖度
    if "quality" in comparison["metrics_delta"]:
        if "path_coverage" in comparison["metrics_delta"]["quality"]:
            coverage = comparison["metrics_delta"]["quality"]["path_coverage"]
            print(f"\n📊 路径覆盖度:")
            print(f"  v1.0 (BFS)       : {coverage['avg_a']:.2%}")
            print(f"  v2.0 (Beam)      : {coverage['avg_b']:.2%}")
            print(f"  变化             : {coverage['delta']:.2%} ({coverage['percent_change']:.1f}%)")
            
            if coverage['delta'] > 0.05:
                print(f"  ✅ 显著改善：路径准确性大幅提升")
    
    # 连通性得分
    if "structural" in comparison["metrics_delta"]:
        if "connectivity_score" in comparison["metrics_delta"]["structural"]:
            conn = comparison["metrics_delta"]["structural"]["connectivity_score"]
            print(f"\n📊 连通性得分:")
            print(f"  v1.0 (BFS)       : {conn['avg_a']:.2f}")
            print(f"  v2.0 (Beam)      : {conn['avg_b']:.2f}")
            print(f"  变化             : {conn['delta']:.2f} ({conn['percent_change']:.1f}%)")
    
    # 2. 分析哪些问题改进最显著
    print("\n" + "="*60)
    print("Per-Query 分析：哪些问题改进最显著")
    print("="*60)
    
    if comparison["per_query_comparison"]:
        # 按分支爆炸比改善程度排序
        improvements = []
        
        for item in comparison["per_query_comparison"]:
            query = item["query"]
            
            # 提取分支爆炸比变化
            branch_delta = None
            if "quality" in item["metrics_delta"]:
                if "branch_explosion_ratio" in item["metrics_delta"]["quality"]:
                    branch_delta = item["metrics_delta"]["quality"]["branch_explosion_ratio"]
            
            if branch_delta and branch_delta["delta"] is not None:
                improvements.append({
                    "query": query,
                    "branch_delta": branch_delta,
                    "test_case_id": item["test_case_id"]
                })
        
        # 排序：改善最大的在前（delta 最负）
        improvements.sort(key=lambda x: x["branch_delta"]["delta"])
        
        print("\n🏆 Top 10 改善最显著的问题:")
        for i, item in enumerate(improvements[:10]):
            print(f"\n{i+1}. {item['query'][:70]}...")
            bd = item["branch_delta"]
            print(f"   分支爆炸: {bd['value_a']:.1f} → {bd['value_b']:.1f} (减少 {abs(bd['delta']):.1f}, {abs(bd['percent_change']):.1f}%)")
        
        print("\n⚠️  Top 5 退化的问题:")
        for i, item in enumerate(improvements[-5:]):
            print(f"\n{i+1}. {item['query'][:70]}...")
            bd = item["branch_delta"]
            print(f"   分支爆炸: {bd['value_a']:.1f} → {bd['value_b']:.1f} (增加 {bd['delta']:.1f}, {bd['percent_change']:.1f}%)")
    
    # 3. 决策建议
    print("\n" + "="*60)
    print("决策建议")
    print("="*60)
    
    # 综合评估
    if "quality" in comparison["metrics_delta"]:
        branch = comparison["metrics_delta"]["quality"].get("branch_explosion_ratio")
        coverage = comparison["metrics_delta"]["quality"].get("path_coverage")
        
        if branch and coverage:
            if branch['delta'] < -5.0 and coverage['delta'] > 0:
                print("\n✅ 强烈推荐：v2.0 在效率和准确性上都有显著提升")
            elif branch['delta'] < 0 and coverage['delta'] > 0:
                print("\n✅ 推荐：v2.0 整体表现更好")
            elif branch['delta'] < 0 and coverage['delta'] < 0:
                print("\n⚠️  权衡：v2.0 更高效但准确性下降，需根据业务需求决策")
            elif branch['delta'] > 0 and coverage['delta'] > 0:
                print("\n⚠️  谨慎：v2.0 准确性提升但效率下降，需评估成本")
            else:
                print("\n⚠️  不推荐：v2.0 整体表现未明显改善")
    
    print("\n=== 对比分析完成 ===")


if __name__ == "__main__":
    main()

