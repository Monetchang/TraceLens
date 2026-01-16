"""
TraceLens Similarity Engine
支持三种相似度计算模式：lexical, embedding, llm
"""
from .base import SimilarityEngine
from .factory import get_similarity_engine

__all__ = ["SimilarityEngine", "get_similarity_engine"]

