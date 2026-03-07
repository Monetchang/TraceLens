"""
TraceLens RAG SDK Client
提供 RAG MVP API 的封装方法
"""
from uuid import UUID
from typing import List, Optional
from .client import TraceLensClient


class RAGClient:
    """RAG API 客户端"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
    ):
        self.client = TraceLensClient(base_url, api_key=api_key)
    
    def retrieval_completed(self, run_id: UUID, query: Optional[str], retrieved_chunks: List[dict]):
        """上报 retrieval_completed 事件"""
        return self.client._post("/api/v1/retrieval/completed", {
            "run_id": str(run_id),
            "query": query,
            "retrieved_chunks": retrieved_chunks
        })
    
    def prompt_built(self, run_id: UUID, prompt_chunks: List[str]):
        """上报 prompt_built 事件"""
        return self.client._post("/api/v1/prompt/built", {
            "run_id": str(run_id),
            "prompt_chunks": prompt_chunks
        })
    
    def answer_generated(self, run_id: UUID, answer: str):
        """上报 answer_generated 事件"""
        return self.client._post("/api/v1/answer/generated", {
            "run_id": str(run_id),
            "answer": answer
        })
    
    def gold_chunks(self, run_id: UUID, gold_chunk_ids: List[str]):
        """上报 gold_chunks 事件（可选）"""
        return self.client._post("/api/v1/gold/chunks", {
            "run_id": str(run_id),
            "gold_chunk_ids": gold_chunk_ids
        })
    
    def run_finished(self, run_id: UUID, status: str = "success"):
        """上报 run_finished 事件"""
        return self.client._post("/api/v1/run/finished", {
            "run_id": str(run_id),
            "status": status
        })
    
    def get_metrics(
        self,
        run_id: UUID,
        prev_run_id: Optional[UUID] = None,
        similarity_mode: str = "lexical"
    ) -> dict:
        """
        获取 run 的 metrics
        
        Args:
            run_id: Run ID
            prev_run_id: 上一版本 Run ID（用于版本对比）
            similarity_mode: 相似度计算模式，可选值：lexical, embedding, llm
        """
        params = []
        if prev_run_id:
            params.append(f"prev_run_id={prev_run_id}")
        if similarity_mode:
            params.append(f"similarity_mode={similarity_mode}")
        
        url = f"/api/v1/run/{run_id}/metrics"
        if params:
            url += "?" + "&".join(params)
        return self.client._get(url)
    
    def get_retrieval_diff(
        self,
        run_id: UUID,
        prev_run_id: UUID,
        similarity_mode: str = "lexical"
    ) -> dict:
        """
        获取两个 run 的 retrieval diff
        
        Args:
            run_id: Run ID
            prev_run_id: 上一版本 Run ID
            similarity_mode: 相似度计算模式，可选值：lexical, embedding, llm
        """
        url = f"/api/v1/run/{run_id}/retrieval_diff?prev_run_id={prev_run_id}"
        if similarity_mode:
            url += f"&similarity_mode={similarity_mode}"
        return self.client._get(url)
