"""
Embedding Similarity Engine
基于 embedding 的相似度计算
"""
import numpy as np
from typing import Optional, Dict, Callable
from .base import SimilarityEngine


class EmbeddingSimilarityEngine(SimilarityEngine):
    """
    Embedding 相似度引擎
    
    需要配置 embedding_function
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.embedding_function: Optional[Callable] = config.get("embedding_function") if config else None
        self.cache: Dict[str, np.ndarray] = {}
    
    def set_embedding_function(self, func: Callable[[str], np.ndarray]):
        """设置 embedding 函数"""
        self.embedding_function = func
    
    def compute(
        self,
        source_text: str,
        target_text: str,
        *,
        context: Optional[Dict] = None
    ) -> float:
        """计算 embedding 余弦相似度"""
        if not source_text or not target_text:
            return 0.0
        
        if not self.embedding_function:
            raise ValueError("Embedding function not configured")
        
        try:
            # 获取 embeddings（带缓存）
            source_emb = self._get_embedding(source_text)
            target_emb = self._get_embedding(target_text)
            
            # 计算余弦相似度
            return self._cosine_similarity(source_emb, target_emb)
        except Exception as e:
            # 如果 embedding 计算失败，返回 0
            print(f"Warning: Embedding computation failed: {e}")
            return 0.0
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """获取文本的 embedding（带缓存）"""
        # 简单的缓存策略：使用文本前 100 个字符作为 key
        cache_key = text[:100] if len(text) > 100 else text
        
        if cache_key not in self.cache:
            emb = self.embedding_function(text)
            self.cache[cache_key] = emb
        
        return self.cache[cache_key]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # 确保在 [0, 1] 范围内
        # 余弦相似度范围是 [-1, 1]，映射到 [0, 1]
        return float(max(0.0, min(1.0, (similarity + 1) / 2)))

