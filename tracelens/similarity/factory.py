"""
Similarity Engine 工厂
"""
from typing import Optional, Dict
from .base import SimilarityEngine
from .lexical import LexicalSimilarityEngine
from .embedding import EmbeddingSimilarityEngine
from .llm_judge import LLMSimilarityEngine


def get_similarity_engine(
    mode: str = "lexical",
    config: Optional[Dict] = None
) -> SimilarityEngine:
    """
    获取相似度引擎
    
    Args:
        mode: 引擎模式，可选值：
            - "lexical": 词法相似度（默认，零配置）
            - "embedding": Embedding 相似度（需要配置 embedding_function）
            - "llm": LLM 判断相似度（需要配置 llm_client）
        config: 引擎配置参数
        
    Returns:
        SimilarityEngine 实例
    """
    mode = mode.lower()
    
    if mode == "lexical":
        return LexicalSimilarityEngine(config)
    elif mode == "embedding":
        return EmbeddingSimilarityEngine(config)
    elif mode == "llm":
        return LLMSimilarityEngine(config)
    else:
        raise ValueError(f"Unknown similarity mode: {mode}. Supported modes: lexical, embedding, llm")


# 全局引擎实例（可选）
_default_engine: Optional[SimilarityEngine] = None


def get_default_engine() -> SimilarityEngine:
    """获取默认引擎（lexical）"""
    global _default_engine
    if _default_engine is None:
        _default_engine = LexicalSimilarityEngine()
    return _default_engine


def set_default_engine(engine: SimilarityEngine):
    """设置默认引擎"""
    global _default_engine
    _default_engine = engine

