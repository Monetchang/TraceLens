"""
TraceLens 批量评测示例
演示如何使用评测系统进行批量测试和版本对比
"""
import sys
sys.path.insert(0, "..")

from uuid import UUID
from sdk.evaluation_client import EvaluationClient
from sdk.rag_client import RAGClient
import time


# 模拟的 RAG 系统
def mock_rag_retrieval(query: str, version: str):
    """模拟检索系统"""
    # 根据 version 返回不同的检索结果
    if version == "v1.0":
        return [
            {"chunk_id": f"chunk_{i}", "content": f"Content for {query} - v1 chunk {i}", "score": 0.9 - i*0.1}
            for i in range(5)
        ]
    else:  # v2.0
        return [
            {"chunk_id": f"chunk_{i}", "content": f"Improved content for {query} - v2 chunk {i}", "score": 0.95 - i*0.05}
            for i in range(5)
        ]


def mock_rag_generation(query: str, chunks: list) -> str:
    """模拟生成系统"""
    return f"Answer to '{query}' based on {len(chunks)} chunks."


def main():
    BASE_URL = "http://localhost:8000"
    eval_client = EvaluationClient(BASE_URL)
    rag_client = RAGClient(BASE_URL)
    
    print("=" * 60)
    print("TraceLens 批量评测示例")
    print("=" * 60)
    
    # ========== Step 1: 创建测试集并上传测试用例 ==========
    print("\n[Step 1] 创建测试集...")
    
    test_suite = eval_client.create_test_suite(
        name="RAG System Test Suite",
        description="标准测试集，包含10个典型问题"
    )
    test_suite_id = UUID(test_suite["id"])
    print(f"✓ 测试集已创建: {test_suite_id}")
    
    # 准备测试用例（10个问题）
    test_cases = [
        {
            "query": "What is RAG?",
            "gold_answer": "RAG stands for Retrieval-Augmented Generation...",
            "gold_chunk_ids": ["chunk_0", "chunk_1"],
            "metadata": {"category": "concept"}
        },
        {
            "query": "How does vector database work?",
            "gold_answer": "Vector databases store embeddings and enable similarity search...",
            "gold_chunk_ids": ["chunk_2", "chunk_3"],
            "metadata": {"category": "technical"}
        },
        {
            "query": "What is the difference between RAG and fine-tuning?",
            "gold_answer": "RAG retrieves external knowledge while fine-tuning updates model weights...",
            "gold_chunk_ids": ["chunk_0", "chunk_4"],
            "metadata": {"category": "comparison"}
        },
    ]
    
    # 扩展到10个问题（这里简化处理）
    for i in range(3, 10):
        test_cases.append({
            "query": f"Test question {i+1}?",
            "gold_chunk_ids": [f"chunk_{i}", f"chunk_{i+1}"],
            "metadata": {"category": "test"}
        })
    
    result = eval_client.upload_test_cases(test_suite_id, test_cases)
    print(f"✓ 已上传 {result['created_count']} 个测试用例")
    
    # ========== Step 2: 运行 v1.0 评测 ==========
    print("\n[Step 2] 运行 v1.0 评测...")
    
    evaluation_v1 = eval_client.create_evaluation(
        name="RAG System v1.0 Evaluation",
        test_suite_id=test_suite_id,
        version_id="v1.0",
        metadata={"embedding_model": "text-embedding-ada-002", "chunk_size": 512}
    )
    eval_v1_id = UUID(evaluation_v1["id"])
    print(f"✓ 评测任务已创建: {eval_v1_id}")
    
    # 获取测试用例并运行
    test_cases_to_run = eval_client.get_evaluation_test_cases(eval_v1_id)
    print(f"✓ 获取到 {len(test_cases_to_run)} 个测试用例，开始运行...")
    
    for idx, test_case in enumerate(test_cases_to_run):
        print(f"  [{idx+1}/{len(test_cases_to_run)}] 运行: {test_case['query'][:50]}...")
        
        # 创建 run，自动关联 test_case
        run = rag_client.start_run(
            name=f"v1.0_test_{idx+1}",
            evaluation_id=eval_v1_id,
            test_case_id=UUID(test_case["id"])
        )
        
        try:
            # 模拟检索
            retrieved_chunks = mock_rag_retrieval(test_case["query"], "v1.0")
            rag_client.retrieval_completed(
                run_id=run.id,
                retrieved_chunks=retrieved_chunks,
                query=test_case["query"]
            )
            
            # 模拟 prompt 构建（使用前3个 chunks）
            prompt_chunks = [c["chunk_id"] for c in retrieved_chunks[:3]]
            rag_client.prompt_built(run.id, prompt_chunks)
            
            # 模拟生成答案
            answer = mock_rag_generation(test_case["query"], retrieved_chunks[:3])
            rag_client.answer_generated(run.id, answer)
            
            # 结束 run
            rag_client.run_finished(run.id, status="success")
            
        except Exception as e:
            print(f"    ✗ 失败: {e}")
            rag_client.run_finished(run.id, status="error")
    
    print("✓ v1.0 评测完成")
    
    # 查看进度
    status_v1 = eval_client.get_evaluation_status(eval_v1_id)
    print(f"  进度: {status_v1['completed_runs']}/{status_v1['total_test_cases']} ({status_v1['progress']*100:.1f}%)")
    
    # ========== Step 3: 获取 v1.0 聚合指标 ==========
    print("\n[Step 3] 获取 v1.0 聚合指标...")
    
    metrics_v1 = eval_client.get_evaluation_metrics(eval_v1_id, similarity_mode="lexical")
    print(f"✓ v1.0 指标 (完成 {metrics_v1['completed_runs']} runs):")
    
    for metric_name, stats in metrics_v1["aggregate_metrics"].items():
        print(f"  - {metric_name}:")
        print(f"      avg: {stats['avg']:.4f}, p50: {stats['p50']:.4f}, p95: {stats['p95']:.4f}")
    
    # ========== Step 4: 运行 v2.0 评测（模拟改进后的系统）==========
    print("\n[Step 4] 运行 v2.0 评测（改进版本）...")
    
    evaluation_v2 = eval_client.create_evaluation(
        name="RAG System v2.0 Evaluation",
        test_suite_id=test_suite_id,
        version_id="v2.0",
        metadata={"embedding_model": "text-embedding-3-large", "chunk_size": 256}
    )
    eval_v2_id = UUID(evaluation_v2["id"])
    print(f"✓ 评测任务已创建: {eval_v2_id}")
    
    test_cases_to_run = eval_client.get_evaluation_test_cases(eval_v2_id)
    print(f"✓ 运行 {len(test_cases_to_run)} 个测试用例...")
    
    for idx, test_case in enumerate(test_cases_to_run):
        print(f"  [{idx+1}/{len(test_cases_to_run)}] 运行: {test_case['query'][:50]}...")
        
        run = rag_client.start_run(
            name=f"v2.0_test_{idx+1}",
            evaluation_id=eval_v2_id,
            test_case_id=UUID(test_case["id"])
        )
        
        try:
            # 模拟检索（v2.0 改进版）
            retrieved_chunks = mock_rag_retrieval(test_case["query"], "v2.0")
            rag_client.retrieval_completed(
                run_id=run.id,
                retrieved_chunks=retrieved_chunks,
                query=test_case["query"]
            )
            
            prompt_chunks = [c["chunk_id"] for c in retrieved_chunks[:3]]
            rag_client.prompt_built(run.id, prompt_chunks)
            
            answer = mock_rag_generation(test_case["query"], retrieved_chunks[:3])
            rag_client.answer_generated(run.id, answer)
            
            rag_client.run_finished(run.id, status="success")
            
        except Exception as e:
            print(f"    ✗ 失败: {e}")
            rag_client.run_finished(run.id, status="error")
    
    print("✓ v2.0 评测完成")
    
    # ========== Step 5: 对比 v1.0 vs v2.0 ==========
    print("\n[Step 5] 对比 v1.0 vs v2.0...")
    
    comparison = eval_client.compare_evaluations(
        eval_a_id=eval_v1_id,
        eval_b_id=eval_v2_id,
        similarity_mode="lexical",
        include_per_query=False
    )
    
    print(f"\n版本对比结果:")
    print(f"  v1.0: {comparison['evaluation_a']['version_id']}")
    print(f"  v2.0: {comparison['evaluation_b']['version_id']}")
    print(f"\n指标变化:")
    
    for metric_name, delta_stats in comparison["metrics_delta"].items():
        avg_a = delta_stats.get("avg_a")
        avg_b = delta_stats.get("avg_b")
        delta = delta_stats.get("delta")
        percent_change = delta_stats.get("percent_change")
        
        if delta is not None and percent_change is not None:
            direction = "↑" if delta > 0 else "↓" if delta < 0 else "="
            print(f"  - {metric_name}:")
            print(f"      {avg_a:.4f} → {avg_b:.4f} ({direction} {abs(percent_change):.2f}%)")
    
    print("\n" + "=" * 60)
    print("评测完成！")
    print("=" * 60)
    print("\n关键发现:")
    print("- 通过批量评测，可以系统化地评估 RAG 系统在多个问题上的表现")
    print("- 版本对比功能帮助量化改进效果（如切换 embedding 模型、调整 chunk size）")
    print("- 聚合指标（avg/p50/p95）平衡整体趋势和异常值")


if __name__ == "__main__":
    main()

