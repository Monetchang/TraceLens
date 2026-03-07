"""
TraceLens GraphRAG Client
用于图推理评测
"""
from uuid import UUID
from typing import List, Optional


class GraphRAGClient:
    """GraphRAG 客户端"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
    ):
        from sdk.client import TraceLensClient

        self.client = TraceLensClient(base_url, api_key=api_key)
    
    def graph_expand(self, run_id: UUID, from_node: str, to_node: str, relation: str, step_index: int):
        """
        上报图扩展事件
        
        Args:
            run_id: Run ID
            from_node: 源节点
            to_node: 目标节点
            relation: 关系类型
            step_index: 推理步骤索引
        """
        return self.client._post("/api/v1/graph/expand", {
            "run_id": str(run_id),
            "from_node": from_node,
            "to_node": to_node,
            "relation": relation,
            "step_index": step_index
        })
    
    def path_selected(self, run_id: UUID, path: List[str]):
        """
        上报路径选择事件
        
        Args:
            run_id: Run ID
            path: 选中的路径（节点 ID 列表）
        """
        return self.client._post("/api/v1/graph/path/selected", {
            "run_id": str(run_id),
            "path": path
        })
    
    def get_graph_metrics(self, run_id: UUID, include_semantic: bool = False) -> dict:
        """
        获取 GraphRAG 指标
        
        Args:
            run_id: Run ID
            include_semantic: 是否包含语义指标（需要 LLM）
        """
        url = f"/api/v1/run/{run_id}/graph-metrics"
        if include_semantic:
            url += "?include_semantic=true"
        return self.client._get(url)
    
    def get_reasoning_path(self, run_id: UUID) -> dict:
        """
        获取推理路径
        
        Args:
            run_id: Run ID
        """
        return self.client._get(f"/api/v1/run/{run_id}/reasoning-path")

