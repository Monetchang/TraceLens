"""
TraceLens RAG MVP - API 接口接入示例
直接使用 HTTP API 调用
"""
import httpx

BASE_URL = "http://localhost:8000"


def main():
    client = httpx.Client(base_url=BASE_URL)
    
    # 1. 创建 run
    run_resp = client.post("/api/v1/run/start", json={
        "name": "api_example_query",
        "metadata": {
            "query": "What is RAG?",
            "version_id": "v1.0"
        }
    })
    run_data = run_resp.json()
    run_id = run_data["id"]
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
        
        client.post("/api/v1/retrieval/completed", json={
            "run_id": str(run_id),
            "query": "What is RAG?",
            "retrieved_chunks": retrieved_chunks
        })
        print(f"Reported {len(retrieved_chunks)} retrieved chunks")
        
        # 3. 上报 prompt_built（构建 prompt 时使用的 chunks）
        prompt_chunk_ids = ["chunk_001", "chunk_002", "chunk_003"]
        client.post("/api/v1/prompt/built", json={
            "run_id": str(run_id),
            "prompt_chunks": prompt_chunk_ids
        })
        print(f"Reported {len(prompt_chunk_ids)} prompt chunks")
        
        # 4. 上报 answer_generated
        answer = "RAG (Retrieval-Augmented Generation) is a technique that combines retrieval and generation to improve language model outputs."
        client.post("/api/v1/answer/generated", json={
            "run_id": str(run_id),
            "answer": answer
        })
        print("Reported answer")
        
        # 5. 结束 run
        client.post("/api/v1/run/finished", json={
            "run_id": str(run_id),
            "status": "success"
        })
        print("Run finished")
        
        # 6. 获取指标（使用默认的 lexical 相似度）
        metrics_resp = client.get(f"/api/v1/run/{run_id}/metrics", params={"similarity_mode": "lexical"})
        metrics = metrics_resp.json()
        print("\n=== 指标（lexical 相似度）===")
        print(f"基础指标: {metrics['metrics']}")
        print(f"扩展指标: {metrics.get('extended_metrics')}")
        
        # 7. 使用不同的相似度模式（可选）
        # 使用 embedding 相似度（需要配置 embedding function）
        # metrics_resp = client.get(f"/api/v1/run/{run_id}/metrics", params={"similarity_mode": "embedding"})
        # metrics = metrics_resp.json()
        # print("\n=== 指标（embedding 相似度）===")
        # print(f"扩展指标: {metrics.get('extended_metrics')}")
        
        # 8. 版本对比（如果有上一版本）
        # print("\n=== 版本对比（lexical 相似度）===")
        # prev_run_id = "..."  # 上一版本的 run_id
        # diff_resp = client.get(f"/api/v1/run/{run_id}/retrieval_diff", params={
        #     "prev_run_id": prev_run_id,
        #     "similarity_mode": "lexical"
        # })
        # diff = diff_resp.json()
        # print(f"new_chunks_ratio: {diff['new_chunks_ratio']}")
        # print(f"rank_deltas: {diff['rank_deltas']}")
        # print(f"new_chunks_query_similarity: {diff['new_chunks_query_similarity']}")
        # print(f"dropped_chunks_query_similarity: {diff['dropped_chunks_query_similarity']}")
        
    except Exception as e:
        client.post("/api/v1/run/finished", json={
            "run_id": str(run_id),
            "status": "error"
        })
        raise


if __name__ == "__main__":
    main()
