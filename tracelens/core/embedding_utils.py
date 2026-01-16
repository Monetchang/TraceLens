"""
Embedding 工具函数
支持使用 sentence-transformers 或自定义 embedding 函数
"""
from typing import Optional, Callable, List
import numpy as np


_embedding_fn: Optional[Callable[[str], List[float]]] = None


def set_embedding_function(fn: Callable[[str], List[float]]):
    """设置全局 embedding 函数"""
    global _embedding_fn
    _embedding_fn = fn


def get_embedding(text: str) -> List[float]:
    """获取文本的 embedding"""
    if _embedding_fn:
        return _embedding_fn(text)
    
    # 默认使用简单的占位实现（实际使用时应该设置 embedding 函数）
    raise ValueError("Embedding function not set. Please call set_embedding_function() first.")


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算余弦相似度"""
    vec1_arr = np.array(vec1)
    vec2_arr = np.array(vec2)
    
    dot_product = np.dot(vec1_arr, vec2_arr)
    norm1 = np.linalg.norm(vec1_arr)
    norm2 = np.linalg.norm(vec2_arr)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))

