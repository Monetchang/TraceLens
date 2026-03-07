from uuid import UUID
from typing import Any, Dict, List, Optional
from sdk.client import TraceLensClient


class EvaluationClient:
    """TraceLens 批量评测客户端"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
    ):
        self.client = TraceLensClient(base_url, api_key=api_key)
    
    # ==================== 测试集管理 ====================
    
    def create_test_suite(self, name: str, description: Optional[str] = None) -> dict:
        """创建测试集"""
        return self.client._post("/api/v1/test_suite", {
            "name": name,
            "description": description
        })
    
    def get_test_suite(self, suite_id: UUID) -> dict:
        """获取测试集详情"""
        return self.client._get(f"/api/v1/test_suite/{suite_id}")
    
    def upload_test_cases(self, suite_id: UUID, test_cases: List[Dict[str, Any]]) -> dict:
        """
        批量上传测试用例（支持 RAG 和 GraphRAG）
        
        Args:
            suite_id: 测试集 ID
            test_cases: 测试用例列表，每个用例包含:
                # RAG gold 数据
                - query (str): 测试问题
                - gold_answer (str, optional): 正确答案
                - gold_chunk_ids (list, optional): 正确检索片段 ID 列表
                - gold_doc_ids (list, optional): 正确文档 ID 列表
                # GraphRAG gold 数据
                - gold_path (list[str], optional): 标准推理路径节点列表
                - gold_nodes (list[str], optional): 应该检索到的关键节点
                - metadata (dict, optional): 其他元数据
        
        Returns:
            {"status": "ok", "created_count": int, "test_case_ids": [str]}
        """
        return self.client._post(f"/api/v1/test_suite/{suite_id}/test_cases", {
            "test_cases": test_cases
        })
    
    def get_test_cases(self, suite_id: UUID, limit: int = 1000, offset: int = 0) -> List[dict]:
        """获取测试集的所有测试用例"""
        return self.client._get(f"/api/v1/test_suite/{suite_id}/test_cases?limit={limit}&offset={offset}")
    
    # ==================== 评测任务管理 ====================
    
    def create_evaluation(
        self, 
        name: str,
        test_suite_id: UUID, 
        version_id: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict:
        """
        创建评测任务
        
        Args:
            name: 评测任务名称
            test_suite_id: 测试集 ID
            version_id: 版本标识（如 "v1.0", "v2.0"）
            metadata: 可选的元数据（如配置信息）
        
        Returns:
            Evaluation 对象字典
        """
        return self.client._post("/api/v1/evaluation", {
            "name": name,
            "test_suite_id": str(test_suite_id),
            "version_id": version_id,
            "metadata": metadata
        })
    
    def get_evaluation(self, evaluation_id: UUID) -> dict:
        """获取评测任务详情"""
        return self.client._get(f"/api/v1/evaluation/{evaluation_id}")
    
    def get_evaluation_test_cases(self, evaluation_id: UUID) -> List[dict]:
        """获取评测任务的测试用例（供 RAG 系统遍历）"""
        return self.client._get(f"/api/v1/evaluation/{evaluation_id}/test_cases")
    
    def get_evaluation_status(self, evaluation_id: UUID) -> dict:
        """
        获取评测进度
        
        Returns:
            {
                "evaluation_id": UUID,
                "status": str,
                "total_test_cases": int,
                "total_runs": int,
                "completed_runs": int,
                "failed_runs": int,
                "progress": float  # 0.0 - 1.0
            }
        """
        return self.client._get(f"/api/v1/evaluation/{evaluation_id}/status")
    
    def get_evaluation_metrics(
        self, 
        evaluation_id: UUID, 
        similarity_mode: str = "lexical",
        include_per_query: bool = False
    ) -> dict:
        """
        获取评测任务的聚合指标
        
        Args:
            evaluation_id: 评测任务 ID
            similarity_mode: 相似度计算模式（lexical/embedding/llm）
            include_per_query: 是否包含每个问题的详细指标
        
        Returns:
            {
                "evaluation_id": UUID,
                "version_id": str,
                "total_runs": int,
                "completed_runs": int,
                "aggregate_metrics": {
                    "metric_name": {
                        "avg": float,
                        "p50": float,
                        "p95": float,
                        "min": float,
                        "max": float
                    }
                },
                "per_query_metrics": [...]  # if include_per_query
            }
        """
        params = {
            "similarity_mode": similarity_mode,
            "include_per_query": str(include_per_query).lower()
        }
        url = f"/api/v1/evaluation/{evaluation_id}/metrics"
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return self.client._get(f"{url}?{query_string}")
    
    # ==================== 版本对比 ====================
    
    def compare_evaluations(
        self,
        eval_a_id: UUID,
        eval_b_id: UUID,
        similarity_mode: str = "lexical",
        include_per_query: bool = False
    ) -> dict:
        """
        对比两个评测任务
        
        Args:
            eval_a_id: 第一个评测任务 ID（通常是旧版本）
            eval_b_id: 第二个评测任务 ID（通常是新版本）
            similarity_mode: 相似度计算模式
            include_per_query: 是否包含每个问题的详细对比
        
        Returns:
            {
                "evaluation_a": {"id": ..., "version_id": ..., "name": ...},
                "evaluation_b": {"id": ..., "version_id": ..., "name": ...},
                "metrics_delta": {
                    "metric_name": {
                        "avg_a": float,
                        "avg_b": float,
                        "delta": float,
                        "percent_change": float,
                        ...
                    }
                },
                "per_query_comparison": [...]  # if include_per_query
            }
        """
        params = {
            "eval_a": str(eval_a_id),
            "eval_b": str(eval_b_id),
            "similarity_mode": similarity_mode,
            "include_per_query": str(include_per_query).lower()
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return self.client._get(f"/api/v1/evaluation/compare?{query_string}")
    
    # ==================== GraphRAG 评测 ====================
    
    def get_graph_evaluation_metrics(
        self, 
        evaluation_id: UUID, 
        include_semantic: bool = False,
        include_per_query: bool = False
    ) -> dict:
        """
        获取 GraphRAG 评测任务的聚合指标
        
        Args:
            evaluation_id: 评测任务 ID
            include_semantic: 是否包含语义指标（LLM Judge）
            include_per_query: 是否包含每个问题的详细指标
        
        Returns:
            {
                "evaluation_id": UUID,
                "name": str,
                "version_id": str,
                "total_runs": int,
                "completed_runs": int,
                "status": str,
                "aggregate_metrics": {
                    "structural": {
                        "path_exists_rate": {"avg": 0.95, "p50": 1.0, "p95": 1.0},
                        "avg_reasoning_hops": {"avg": 3.2, "p50": 3.0, "p95": 5.0},
                        "avg_connectivity_score": {"avg": 0.75, "p50": 0.80, "p95": 0.95}
                    },
                    "quality": {
                        "avg_branch_explosion_ratio": {"avg": 8.5, "p50": 7.0, "p95": 15.0},
                        "avg_path_coverage": {"avg": 0.72, "p50": 0.75, "p95": 0.90}
                    },
                    "semantic": {
                        "avg_path_relevance_score": {"avg": 0.78, "p50": 0.80, "p95": 0.90}
                    }
                },
                "per_query_metrics": [...]  # if include_per_query
            }
        """
        params = {
            "include_semantic": str(include_semantic).lower(),
            "include_per_query": str(include_per_query).lower()
        }
        url = f"/api/v1/evaluation/{evaluation_id}/graph_metrics"
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return self.client._get(f"{url}?{query_string}")
    
    def compare_graph_evaluations(
        self,
        eval_a_id: UUID,
        eval_b_id: UUID,
        include_semantic: bool = False,
        include_per_query: bool = False
    ) -> dict:
        """
        对比两个 GraphRAG 评测任务
        
        Args:
            eval_a_id: 第一个评测任务 ID（通常是旧版本）
            eval_b_id: 第二个评测任务 ID（通常是新版本）
            include_semantic: 是否包含语义指标
            include_per_query: 是否包含每个问题的详细对比
        
        Returns:
            {
                "evaluation_a": {"id": ..., "version_id": "v1.0_BFS", "name": ...},
                "evaluation_b": {"id": ..., "version_id": "v2.0_BeamSearch", "name": ...},
                "metrics_delta": {
                    "structural": {
                        "avg_reasoning_hops": {
                            "avg_a": 4.5, "avg_b": 3.2,
                            "delta": -1.3, "percent_change": -28.9
                        }
                    },
                    "quality": {
                        "avg_branch_explosion_ratio": {
                            "avg_a": 15.2, "avg_b": 8.5,
                            "delta": -6.7, "percent_change": -44.1
                        }
                    }
                },
                "per_query_comparison": [...]  # if include_per_query
            }
        """
        params = {
            "eval_a": str(eval_a_id),
            "eval_b": str(eval_b_id),
            "include_semantic": str(include_semantic).lower(),
            "include_per_query": str(include_per_query).lower()
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return self.client._get(f"/api/v1/evaluation/graph_compare?{query_string}")

