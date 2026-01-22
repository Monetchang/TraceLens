"""
GraphRAG 批量评测示例
演示如何评估剪枝策略优化效果
"""
from uuid import UUID
from sdk.evaluation_client import EvaluationClient
from sdk.client import TraceLensClient


def main():
    # 1. 初始化客户端
    eval_client = EvaluationClient(base_url="http://localhost:8000")
    tracelens = TraceLensClient(base_url="http://localhost:8000")
    
    # 2. 创建测试集
    print("\n=== 创建测试集 ===")
    test_suite = eval_client.create_test_suite(
        name="GraphRAG Reasoning Test Suite",
        description="50个多跳推理测试问题"
    )
    print(f"✅ 测试集已创建: {test_suite['id']}")
    
    # 3. 上传测试用例（包含 GraphRAG gold 数据）
    print("\n=== 上传测试用例 ===")
    test_cases = [
        {
            "query": "Alice 和 Project_AI 的关系",
            "gold_answer": "Alice works at Company X, which runs Project AI.",
            "gold_path": ["Alice", "Company_X", "Project_AI"],  # 标准推理路径
            "gold_nodes": ["Alice", "Company_X", "Project_AI"],
            "metadata": {"hops": 2, "type": "entity_relation"}
        },
        {
            "query": "Bob 参与了哪些项目？",
            "gold_answer": "Bob contributes to Project Beta and Project Gamma.",
            "gold_path": ["Bob", "Team_Engineering", "Project_Beta"],
            "gold_nodes": ["Bob", "Team_Engineering", "Project_Beta", "Project_Gamma"],
            "metadata": {"hops": 2, "type": "entity_relation"}
        },
        {
            "query": "Team_ML 和 Product_X 的关系",
            "gold_answer": "Team ML develops AI features for Product X.",
            "gold_path": ["Team_ML", "Feature_AI_Recommend", "Product_X"],
            "gold_nodes": ["Team_ML", "Feature_AI_Recommend", "Product_X"],
            "metadata": {"hops": 2, "type": "team_product"}
        },
        # ... 更多测试用例
    ]
    
    result = eval_client.upload_test_cases(UUID(test_suite["id"]), test_cases)
    print(f"✅ 已上传 {result['created_count']} 个测试用例")
    
    # 4. 创建评测任务 v1.0（使用 BFS 策略）
    print("\n=== 创建评测任务 v1.0 (BFS) ===")
    evaluation_v1 = eval_client.create_evaluation(
        name="GraphRAG v1.0 Evaluation (BFS)",
        test_suite_id=UUID(test_suite["id"]),
        version_id="v1.0_BFS",
        metadata={"search_strategy": "BFS", "max_hops": 5}
    )
    print(f"✅ 评测任务 v1.0 已创建: {evaluation_v1['id']}")
    
    # 5. 运行评测 v1.0
    print("\n=== 运行评测 v1.0 ===")
    test_cases_to_run = eval_client.get_evaluation_test_cases(UUID(evaluation_v1["id"]))
    
    for i, tc in enumerate(test_cases_to_run):
        print(f"  运行测试用例 {i+1}/{len(test_cases_to_run)}: {tc['query'][:50]}...")
        
        # 启动 run
        run = tracelens.start_run(
            name=f"v1.0_test_{i+1}",
            metadata={
                "evaluation_id": str(evaluation_v1["id"]),
                "test_case_id": str(tc["id"])
            }
        )
        
        # 这里调用你的 GraphRAG 系统
        # your_graphrag_system.run(tc["query"], run.id)
        # 
        # 假设你的 GraphRAG 系统已经通过以下 API 上报了数据：
        # - POST /api/v1/graph/node/expanded - 上报扩展的节点
        # - POST /api/v1/graph/edge/traversed - 上报遍历的边
        # - POST /api/v1/graph/path/selected - 上报选中的推理路径
        # - POST /api/v1/answer/generated - 上报生成的答案
        
        # 示例：模拟 GraphRAG 系统运行
        # （实际使用时，替换为你的 GraphRAG 系统调用）
        simulate_graphrag_run(tracelens, run.id, tc["query"])
        
        # 结束 run
        tracelens.end_run(run.id, status="success")
    
    print(f"✅ v1.0 评测完成")
    
    # 6. 获取 v1.0 聚合指标
    print("\n=== v1.0 聚合指标 ===")
    metrics_v1 = eval_client.get_graph_evaluation_metrics(UUID(evaluation_v1["id"]))
    
    print(f"总 runs: {metrics_v1['total_runs']}")
    print(f"成功 runs: {metrics_v1['completed_runs']}")
    print("\n结构性指标:")
    if "structural" in metrics_v1["aggregate_metrics"]:
        for metric_name, stats in metrics_v1["aggregate_metrics"]["structural"].items():
            print(f"  {metric_name}: avg={stats['avg']:.2f}, p50={stats['p50']:.2f}, p95={stats['p95']:.2f}")
    
    print("\n质量指标:")
    if "quality" in metrics_v1["aggregate_metrics"]:
        for metric_name, stats in metrics_v1["aggregate_metrics"]["quality"].items():
            print(f"  {metric_name}: avg={stats['avg']:.2f}, p50={stats['p50']:.2f}, p95={stats['p95']:.2f}")
    
    # 7. 创建评测任务 v2.0（使用 Beam Search 策略 + 优化剪枝）
    print("\n=== 创建评测任务 v2.0 (Beam Search) ===")
    evaluation_v2 = eval_client.create_evaluation(
        name="GraphRAG v2.0 Evaluation (Beam Search)",
        test_suite_id=UUID(test_suite["id"]),
        version_id="v2.0_BeamSearch",
        metadata={"search_strategy": "BeamSearch", "beam_size": 3, "max_hops": 4}
    )
    print(f"✅ 评测任务 v2.0 已创建: {evaluation_v2['id']}")
    
    # 8. 运行评测 v2.0（代码类似 v1.0，此处省略）
    print("\n=== 运行评测 v2.0 ===")
    print("  (省略详细过程，与 v1.0 类似)")
    # ... 运行 v2.0 评测 ...
    
    # 9. 版本对比
    print("\n=== 版本对比: v1.0 vs v2.0 ===")
    comparison = eval_client.compare_graph_evaluations(
        eval_a_id=UUID(evaluation_v1["id"]),
        eval_b_id=UUID(evaluation_v2["id"])
    )
    
    print(f"\nv1.0: {comparison['evaluation_a']['version_id']}")
    print(f"v2.0: {comparison['evaluation_b']['version_id']}")
    
    print("\n指标变化:")
    
    # 分析分支爆炸比
    if "quality" in comparison["metrics_delta"]:
        if "branch_explosion_ratio" in comparison["metrics_delta"]["quality"]:
            branch_delta = comparison["metrics_delta"]["quality"]["branch_explosion_ratio"]
            print(f"\n📊 分支爆炸比:")
            print(f"  v1.0: {branch_delta['avg_a']:.2f}")
            print(f"  v2.0: {branch_delta['avg_b']:.2f}")
            print(f"  变化: {branch_delta['delta']:.2f} ({branch_delta['percent_change']:.1f}%)")
            
            if branch_delta['delta'] < 0:
                print(f"  ✅ 改善: 剪枝策略优化有效，分支爆炸减少 {abs(branch_delta['percent_change']):.1f}%")
            else:
                print(f"  ⚠️  退化: 分支爆炸增加 {branch_delta['percent_change']:.1f}%")
    
    # 分析推理跳数
    if "structural" in comparison["metrics_delta"]:
        if "reasoning_hops" in comparison["metrics_delta"]["structural"]:
            hops_delta = comparison["metrics_delta"]["structural"]["reasoning_hops"]
            print(f"\n📊 推理跳数:")
            print(f"  v1.0: {hops_delta['avg_a']:.2f}")
            print(f"  v2.0: {hops_delta['avg_b']:.2f}")
            print(f"  变化: {hops_delta['delta']:.2f} 跳")
    
    # 分析路径覆盖度
    if "quality" in comparison["metrics_delta"]:
        if "path_coverage" in comparison["metrics_delta"]["quality"]:
            coverage_delta = comparison["metrics_delta"]["quality"]["path_coverage"]
            print(f"\n📊 路径覆盖度:")
            print(f"  v1.0: {coverage_delta['avg_a']:.2f}")
            print(f"  v2.0: {coverage_delta['avg_b']:.2f}")
            print(f"  变化: {coverage_delta['delta']:.2f} ({coverage_delta['percent_change']:.1f}%)")
            
            if coverage_delta['delta'] > 0:
                print(f"  ✅ 改善: 路径准确性提升 {coverage_delta['percent_change']:.1f}%")
    
    print("\n=== 评测完成 ===")


def simulate_graphrag_run(client: TraceLensClient, run_id: UUID, query: str):
    """
    模拟 GraphRAG 系统运行
    实际使用时，替换为你的 GraphRAG 系统调用
    """
    # 示例：上报扩展的节点
    # client._post("/api/v1/graph/node/expanded", {
    #     "run_id": str(run_id),
    #     "node_id": "Alice",
    #     "node_type": "Person",
    #     "content": "Alice is a software engineer.",
    #     "metadata": {}
    # })
    
    # 示例：上报遍历的边
    # client._post("/api/v1/graph/edge/traversed", {
    #     "run_id": str(run_id),
    #     "from_node": "Alice",
    #     "to_node": "Company_X",
    #     "relation": "works_at",
    #     "metadata": {}
    # })
    
    # 示例：上报选中的推理路径
    # client._post("/api/v1/graph/path/selected", {
    #     "run_id": str(run_id),
    #     "from_node": "Alice",
    #     "to_node": "Company_X",
    #     "relation": "works_at",
    #     "reasoning": "Alice is an employee of Company X"
    # })
    
    # 示例：上报生成的答案
    # client._post("/api/v1/answer/generated", {
    #     "run_id": str(run_id),
    #     "answer": "Alice works at Company X, which runs Project AI."
    # })
    
    pass


if __name__ == "__main__":
    main()

