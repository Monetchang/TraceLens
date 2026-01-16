"""
TraceLens GraphRAG 版本对比示例
演示如何对比两个 GraphRAG 版本的推理质量
"""
import sys
sys.path.insert(0, "..")

from uuid import UUID
from sdk.client import TraceLensClient
from sdk.graph_client import GraphRAGClient

BASE_URL = "http://localhost:8000"


def run_graphrag_v1(base_client, graph_client):
    """运行 GraphRAG v1.0（baseline）"""
    print("\n" + "=" * 60)
    print("运行 GraphRAG v1.0（baseline）")
    print("=" * 60)
    
    run = base_client.start_run(
        name="graphrag_v1_baseline",
        metadata={
            "query": "How is Alice connected to Project_AI?",
            "version": "v1.0",
            "strategy": "BFS with max_hops=3"
        }
    )
    run_id = run.id
    print(f"Created run: {run_id}")
    
    # 模拟 v1.0 推理（BFS，探索较多）
    print("\nv1.0 推理过程（BFS，探索多条路径）:")
    
    # 起点：Alice
    step = 1
    
    # 探索 Alice 的所有邻居
    graph_client.graph_expand(run_id, "Alice", "Company_X", "works_at", step)
    print(f"Step {step}: Alice --[works_at]-> Company_X")
    step += 1
    
    graph_client.graph_expand(run_id, "Alice", "Bob", "knows", step)
    print(f"Step {step}: Alice --[knows]-> Bob")
    step += 1
    
    graph_client.graph_expand(run_id, "Alice", "Charlie", "knows", step)
    print(f"Step {step}: Alice --[knows]-> Charlie")
    step += 1
    
    # 从 Company_X 继续探索
    graph_client.graph_expand(run_id, "Company_X", "Project_AI", "runs", step)
    print(f"Step {step}: Company_X --[runs]-> Project_AI")
    step += 1
    
    graph_client.graph_expand(run_id, "Company_X", "City_Z", "located_in", step)
    print(f"Step {step}: Company_X --[located_in]-> City_Z")
    step += 1
    
    # 从 Bob 继续探索
    graph_client.graph_expand(run_id, "Bob", "Company_Y", "works_at", step)
    print(f"Step {step}: Bob --[works_at]-> Company_Y")
    step += 1
    
    # 从 Charlie 继续探索
    graph_client.graph_expand(run_id, "Charlie", "University", "studies_at", step)
    print(f"Step {step}: Charlie --[studies_at]-> University")
    step += 1
    
    # 选择路径：Alice -> Company_X -> Project_AI
    selected_path = ["Alice", "Company_X", "Project_AI"]
    graph_client.path_selected(run_id, selected_path)
    print(f"\n选中路径: {' -> '.join(selected_path)}")
    
    answer = "Alice works at Company X, which runs Project AI."
    base_client.end_run(run_id, status="success", metadata={"answer": answer})
    
    return run_id


def run_graphrag_v2(base_client, graph_client):
    """运行 GraphRAG v2.0（优化剪枝策略）"""
    print("\n" + "=" * 60)
    print("运行 GraphRAG v2.0（优化剪枝）")
    print("=" * 60)
    
    run = base_client.start_run(
        name="graphrag_v2_pruned",
        metadata={
            "query": "How is Alice connected to Project_AI?",
            "version": "v2.0",
            "strategy": "Beam search with early pruning"
        }
    )
    run_id = run.id
    print(f"Created run: {run_id}")
    
    # 模拟 v2.0 推理（剪枝优化，探索更少）
    print("\nv2.0 推理过程（剪枝优化，更聚焦）:")
    
    step = 1
    
    # 只探索高相关性路径
    graph_client.graph_expand(run_id, "Alice", "Company_X", "works_at", step)
    print(f"Step {step}: Alice --[works_at]-> Company_X")
    step += 1
    
    graph_client.graph_expand(run_id, "Company_X", "Project_AI", "runs", step)
    print(f"Step {step}: Company_X --[runs]-> Project_AI")
    step += 1
    
    # 选择路径：Alice -> Company_X -> Project_AI（与 v1 相同）
    selected_path = ["Alice", "Company_X", "Project_AI"]
    graph_client.path_selected(run_id, selected_path)
    print(f"\n选中路径: {' -> '.join(selected_path)}")
    
    answer = "Alice works at Company X, which runs Project AI."
    base_client.end_run(run_id, status="success", metadata={"answer": answer})
    
    return run_id


def main():
    # 初始化客户端
    base_client = TraceLensClient(BASE_URL)
    graph_client = GraphRAGClient(BASE_URL)
    
    print("=" * 60)
    print("TraceLens GraphRAG 版本对比示例")
    print("=" * 60)
    
    try:
        # 运行两个版本
        run_v1_id = run_graphrag_v1(base_client, graph_client)
        run_v2_id = run_graphrag_v2(base_client, graph_client)
        
        # 对比指标
        print("\n" + "=" * 60)
        print("版本对比分析")
        print("=" * 60)
        
        # 获取 v1.0 指标
        metrics_v1 = graph_client.get_graph_metrics(run_v1_id)
        print("\nv1.0 指标:")
        print(f"  reasoning_hops: {metrics_v1['structural_metrics']['reasoning_hops']}")
        print(f"  connectivity_score: {metrics_v1['structural_metrics']['connectivity_score']:.2f}")
        print(f"  branch_explosion_ratio: {metrics_v1['quality_metrics']['branch_explosion_ratio']:.2f}x")
        
        # 获取 v2.0 指标
        metrics_v2 = graph_client.get_graph_metrics(run_v2_id)
        print("\nv2.0 指标:")
        print(f"  reasoning_hops: {metrics_v2['structural_metrics']['reasoning_hops']}")
        print(f"  connectivity_score: {metrics_v2['structural_metrics']['connectivity_score']:.2f}")
        print(f"  branch_explosion_ratio: {metrics_v2['quality_metrics']['branch_explosion_ratio']:.2f}x")
        
        # 分析差异
        print("\n" + "=" * 60)
        print("核心发现")
        print("=" * 60)
        
        v1_hops = metrics_v1['structural_metrics']['reasoning_hops']
        v2_hops = metrics_v2['structural_metrics']['reasoning_hops']
        print(f"\n1. 推理跳数: v1={v1_hops}, v2={v2_hops} (相同)")
        
        v1_explosion = metrics_v1['quality_metrics']['branch_explosion_ratio']
        v2_explosion = metrics_v2['quality_metrics']['branch_explosion_ratio']
        reduction = (1 - v2_explosion / v1_explosion) * 100
        print(f"\n2. 分支爆炸比:")
        print(f"   v1.0: {v1_explosion:.2f}x（探索了 {v1_explosion:.1f} 倍的节点）")
        print(f"   v2.0: {v2_explosion:.2f}x（探索了 {v2_explosion:.1f} 倍的节点）")
        print(f"   ↓ 减少了 {reduction:.1f}%")
        
        v1_conn = metrics_v1['structural_metrics']['connectivity_score']
        v2_conn = metrics_v2['structural_metrics']['connectivity_score']
        print(f"\n3. 连通性:")
        print(f"   v1.0: {v1_conn:.2f}")
        print(f"   v2.0: {v2_conn:.2f}")
        
        print("\n✓ 结论:")
        print("  • v2.0 保持了相同的推理路径质量")
        print(f"  • v2.0 显著减少了不必要的探索（减少 {reduction:.1f}%）")
        print("  • v2.0 的剪枝策略更高效")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

