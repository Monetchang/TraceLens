"""
TraceLens RAG MVP - SDK 接入示例
使用 TraceLens RAG SDK
"""
import sys
sys.path.insert(0, "..")

from uuid import UUID
from sdk.rag_client import RAGClient
from sdk.client import TraceLensClient

BASE_URL = "http://localhost:8000"


def main():
    # 初始化基础 Client（用于创建 run）
    base_client = TraceLensClient(BASE_URL)
    # 初始化 RAG Client
    rag_client = RAGClient(BASE_URL)
    
    # 1. 创建 run
    run = base_client.start_run(
        name="rag_sdk_example_query",
        metadata={
            "query": "What is RAG?",
            "version_id": "v1.0"
        }
    )
    run_id = run.id
    print(f"Created run: {run_id}")
    
    try:
        # 2. 上报 retrieval_completed
        retrieved_chunks = [
            {"chunk_id": "chunk_001", "score": 0.95, "content": "RAG stands for Retrieval-Augmented Generation..."},
            {"chunk_id": "chunk_002", "score": 0.87, "content": "RAG combines retrieval and generation..."},
            {"chunk_id": "chunk_003", "score": 0.72, "content": "The architecture of RAG includes..."},
            {"chunk_id": "chunk_004", "score": 0.65, "content": "Some unrelated content about databases..."},
            {"chunk_id": "chunk_005", "score": 0.55, "content": "More unrelated content..."},
        ]
        
        rag_client.retrieval_completed(run_id, "What is RAG?", retrieved_chunks)
        print(f"Reported {len(retrieved_chunks)} retrieved chunks")
        
        # 3. 上报 prompt_built
        prompt_chunk_ids = ["chunk_001", "chunk_002", "chunk_003"]
        rag_client.prompt_built(run_id, prompt_chunk_ids)
        print(f"Reported {len(prompt_chunk_ids)} prompt chunks")
        
        # 4. 上报 answer_generated
        answer = "RAG (Retrieval-Augmented Generation) is a technique that combines retrieval and generation to improve language model outputs."
        rag_client.answer_generated(run_id, answer)
        print("Reported answer")
        
        # 5. 结束 run
        rag_client.run_finished(run_id, "success")
        print("Run finished")
        
        # 6. 获取指标（使用默认的 lexical 相似度）
        metrics = rag_client.get_metrics(run_id, similarity_mode="lexical")
        print("\n=== 指标（lexical 相似度）===")
        print(f"基础指标: {metrics['metrics']}")
        print(f"扩展指标: {metrics.get('extended_metrics')}")
        
        # 7. 使用不同的相似度模式（可选）
        # 使用 embedding 相似度（需要配置 embedding function）
        # metrics = rag_client.get_metrics(run_id, similarity_mode="embedding")
        # print("\n=== 指标（embedding 相似度）===")
        # print(f"扩展指标: {metrics.get('extended_metrics')}")
        
        # 8. 版本对比（如果有上一版本）
        # print("\n=== 版本对比（lexical 相似度）===")
        # prev_run_id = UUID("...")  # 上一版本的 run_id
        # diff = rag_client.get_retrieval_diff(run_id, prev_run_id, similarity_mode="lexical")
        # print(f"new_chunks_ratio: {diff['new_chunks_ratio']}")
        # print(f"rank_deltas: {diff['rank_deltas']}")
        # print(f"new_chunks_query_similarity: {diff['new_chunks_query_similarity']}")
        # print(f"dropped_chunks_query_similarity: {diff['dropped_chunks_query_similarity']}")
        
    except Exception as e:
        rag_client.run_finished(run_id, "error")
        raise


if __name__ == "__main__":
    main()
