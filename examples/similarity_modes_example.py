"""
TraceLens RAG MVP - 相似度模式示例
演示如何使用不同的相似度计算模式：lexical, embedding, llm
"""
import sys
sys.path.insert(0, "..")

from uuid import UUID
from sdk.rag_client import RAGClient
from sdk.client import TraceLensClient

BASE_URL = "http://localhost:8000"


def run_example_with_similarity_mode(base_client, rag_client, similarity_mode: str):
    """使用指定的相似度模式运行示例"""
    print(f"\n{'='*60}")
    print(f"使用相似度模式: {similarity_mode}")
    print(f"{'='*60}")
    
    # 1. 创建 run
    run = base_client.start_run(
        name=f"similarity_example_{similarity_mode}",
        metadata={
            "query": "What is RAG?",
            "similarity_mode": similarity_mode
        }
    )
    run_id = run.id
    print(f"Created run: {run_id}")
    
    try:
        # 2. 上报检索结果
        retrieved_chunks = [
            {"chunk_id": "chunk_001", "score": 0.95, "content": "RAG stands for Retrieval-Augmented Generation. It is a technique that combines retrieval and generation to improve language model outputs."},
            {"chunk_id": "chunk_002", "score": 0.87, "content": "RAG improves language models by retrieving relevant context from a knowledge base before generating responses."},
            {"chunk_id": "chunk_003", "score": 0.72, "content": "The RAG architecture includes a retriever component and a generator component working together."},
        ]
        
        rag_client.retrieval_completed(run_id, "What is RAG?", retrieved_chunks)
        print(f"Reported {len(retrieved_chunks)} retrieved chunks")
        
        # 3. 上报 prompt chunks
        prompt_chunk_ids = ["chunk_001", "chunk_002"]
        rag_client.prompt_built(run_id, prompt_chunk_ids)
        print(f"Reported {len(prompt_chunk_ids)} prompt chunks")
        
        # 4. 上报 answer
        answer = "RAG (Retrieval-Augmented Generation) is a technique that combines retrieval and generation. It retrieves relevant context from a knowledge base and then generates responses based on that context, improving the accuracy and relevance of language model outputs."
        rag_client.answer_generated(run_id, answer)
        print("Reported answer")
        
        # 5. 结束 run
        rag_client.run_finished(run_id, "success")
        print("Run finished")
        
        # 6. 获取指标
        metrics = rag_client.get_metrics(run_id, similarity_mode=similarity_mode)
        print(f"\n--- 指标结果 ---")
        print(f"基础指标: {metrics['metrics']}")
        if metrics.get('extended_metrics'):
            print(f"\n扩展指标:")
            for key, value in metrics['extended_metrics'].items():
                print(f"  {key}: {value:.4f}")
        
        return run_id
        
    except Exception as e:
        rag_client.run_finished(run_id, "error")
        print(f"Error: {e}")
        raise


def main():
    # 初始化客户端
    base_client = TraceLensClient(BASE_URL)
    rag_client = RAGClient(BASE_URL)
    
    print("=" * 60)
    print("TraceLens 相似度模式对比示例")
    print("=" * 60)
    
    # 1. 使用 lexical 相似度（默认，零配置）
    print("\n【模式 1】Lexical 相似度")
    print("- 特点：零配置，基于词法的 TF-IDF 余弦相似度")
    print("- 适用场景：快速评估，低成本，无需外部依赖")
    run_lexical = run_example_with_similarity_mode(base_client, rag_client, "lexical")
    
    # 2. 使用 embedding 相似度（需要配置 embedding function）
    # print("\n【模式 2】Embedding 相似度")
    # print("- 特点：基于 embedding 的语义相似度")
    # print("- 适用场景：更准确的语义理解，需要配置 embedding function")
    # 注意：需要在服务端配置 embedding function
    # run_embedding = run_example_with_similarity_mode(base_client, rag_client, "embedding")
    
    # 3. 使用 LLM 相似度（需要配置 LLM client）
    # print("\n【模式 3】LLM Judge 相似度")
    # print("- 特点：使用 LLM 进行相似度判断，最准确但成本最高")
    # print("- 适用场景：高精度评估，benchmark 测试")
    # 注意：需要在服务端配置 LLM client
    # run_llm = run_example_with_similarity_mode(base_client, rag_client, "llm")
    
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print("✅ Lexical 模式：零配置即可使用，适合日常开发和快速评估")
    print("⚡ Embedding 模式：需要配置 embedding function，语义理解更准确")
    print("🎯 LLM 模式：需要配置 LLM client，最准确但成本最高")
    print("\n建议：从 lexical 模式开始，根据需要逐步升级到 embedding 或 LLM 模式")


if __name__ == "__main__":
    main()

