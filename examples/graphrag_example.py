"""
TraceLens GraphRAG MVP 示例
演示如何使用 TraceLens 评测 GraphRAG 推理路径质量
"""
import sys
sys.path.insert(0, "..")

from uuid import UUID
from sdk.client import TraceLensClient
from sdk.graph_client import GraphRAGClient

BASE_URL = "http://localhost:8000"


def main():
    # 初始化客户端
    base_client = TraceLensClient(BASE_URL)
    graph_client = GraphRAGClient(BASE_URL)
    
    print("=" * 60)
    print("TraceLens GraphRAG 推理路径评测示例")
    print("=" * 60)
    
    try:
        # 1. 创建 run
        run = base_client.start_run(
            name="graphrag_reasoning_example",
            metadata={
                "query": "What is the relationship between Alice and Company X?",
                "type": "graphrag"
            }
        )
        run_id = run.id
        print(f"\n✓ Created run: {run_id}")
        
        # 2. 模拟 GraphRAG 推理过程
        print("\n--- GraphRAG 推理过程 ---")
        
        # Step 0: 从 Alice 开始
        print("Step 0: Start from 'Alice'")
        
        # Step 1: Alice --[works_at]-> Company X
        graph_client.graph_expand(
            run_id=run_id,
            from_node="Alice",
            to_node="Company_X",
            relation="works_at",
            step_index=1
        )
        print("Step 1: Alice --[works_at]-> Company_X")
        
        # Step 2: Alice --[knows]-> Bob（探索但未选中）
        graph_client.graph_expand(
            run_id=run_id,
            from_node="Alice",
            to_node="Bob",
            relation="knows",
            step_index=2
        )
        print("Step 2: Alice --[knows]-> Bob (探索)")
        
        # Step 3: Bob --[works_at]-> Company_Y（探索但未选中）
        graph_client.graph_expand(
            run_id=run_id,
            from_node="Bob",
            to_node="Company_Y",
            relation="works_at",
            step_index=3
        )
        print("Step 3: Bob --[works_at]-> Company_Y (探索)")
        
        # Step 4: Company_X --[located_in]-> City_Z（继续探索）
        graph_client.graph_expand(
            run_id=run_id,
            from_node="Company_X",
            to_node="City_Z",
            relation="located_in",
            step_index=4
        )
        print("Step 4: Company_X --[located_in]-> City_Z (探索)")
        
        # 3. 选择最终推理路径
        selected_path = ["Alice", "Company_X"]
        graph_client.path_selected(run_id, selected_path)
        print(f"\n✓ Selected reasoning path: {' -> '.join(selected_path)}")
        
        # 4. 生成答案
        answer = "Alice works at Company X."
        base_client.end_run(run_id, status="success", metadata={"answer": answer})
        print(f"✓ Generated answer: {answer}")
        
        # 5. 获取推理路径
        print("\n--- 推理路径分析 ---")
        path_data = graph_client.get_reasoning_path(run_id)
        
        print(f"选中路径 ({len(path_data['selected_path'])} 步):")
        for step in path_data['selected_path']:
            print(f"  {step['from_node']} --[{step['relation']}]-> {step['to_node']}")
        
        print(f"\n所有探索路径 ({len(path_data['all_traces'])} 步):")
        for step in path_data['all_traces']:
            selected = "✓" if step['is_selected'] else "✗"
            print(f"  [{selected}] {step['from_node']} --[{step['relation']}]-> {step['to_node']}")
        
        # 6. 获取 GraphRAG 指标（结构性）
        print("\n--- GraphRAG 指标（结构性）---")
        metrics = graph_client.get_graph_metrics(run_id, include_semantic=False)
        
        structural = metrics['structural_metrics']
        print(f"path_exists: {structural['path_exists']}")
        print(f"reasoning_hops: {structural['reasoning_hops']}")
        print(f"connectivity_score: {structural['connectivity_score']:.2f}")
        
        if metrics.get('quality_metrics'):
            quality = metrics['quality_metrics']
            print(f"\nbranch_explosion_ratio: {quality['branch_explosion_ratio']:.2f}")
            if 'path_coverage' in quality:
                print(f"path_coverage: {quality['path_coverage']:.2f}")
        
        # 7. 获取语义指标（可选，需要配置 LLM）
        # print("\n--- GraphRAG 指标（语义）---")
        # metrics_semantic = graph_client.get_graph_metrics(run_id, include_semantic=True)
        # if metrics_semantic.get('semantic_metrics'):
        #     semantic = metrics_semantic['semantic_metrics']
        #     print(f"path_relevance_score: {semantic['path_relevance_score']:.2f}")
        
        print("\n" + "=" * 60)
        print("✓ GraphRAG 推理路径评测完成")
        print("=" * 60)
        
        print("\n核心发现：")
        print("1. 推理路径存在且连贯")
        print(f"2. 推理跳数: {structural['reasoning_hops']}")
        print(f"3. 分支爆炸比: {quality['branch_explosion_ratio']:.2f}x")
        print("4. 推理路径高度连通")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

