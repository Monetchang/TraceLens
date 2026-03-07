"""
Similarity Engine 工厂
"""
import logging
from typing import Callable, Dict, Optional

from .base import SimilarityEngine
from .lexical import LexicalSimilarityEngine
from .embedding import EmbeddingSimilarityEngine
from .llm_judge import LLMSimilarityEngine

logger = logging.getLogger(__name__)


def _build_embedding_from_config() -> Optional[Callable]:
    """从环境变量构建 embedding 函数（HTTP endpoint）"""
    from tracelens.config import EMBEDDING_ENDPOINT, EMBEDDING_API_KEY
    if not EMBEDDING_ENDPOINT:
        return None
    import httpx
    import numpy as np
    headers = {"Authorization": f"Bearer {EMBEDDING_API_KEY}"} if EMBEDDING_API_KEY else {}

    def _embed(text: str):
        with httpx.Client(timeout=30.0) as c:
            r = c.post(EMBEDDING_ENDPOINT, json={"input": text}, headers=headers)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and "data" in data:
                return np.array(data["data"][0]["embedding"])
            if isinstance(data, list):
                return np.array(data[0])
            return np.array(data)

    return _embed


def _build_llm_from_config() -> Optional[Callable]:
    """从环境变量构建 LLM 客户端（OpenAI-compatible HTTP endpoint）"""
    from tracelens.config import LLM_ENDPOINT, LLM_API_KEY
    if not LLM_ENDPOINT:
        return None
    import httpx
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"} if LLM_API_KEY else {}

    def _complete(prompt: str) -> str:
        with httpx.Client(timeout=60.0) as c:
            r = c.post(
                LLM_ENDPOINT,
                json={"model": "gpt-4", "messages": [{"role": "user", "content": prompt}]},
                headers=headers,
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

    return _complete


def get_similarity_engine(
    mode: str = "lexical",
    config: Optional[Dict] = None
) -> SimilarityEngine:
    """
    获取相似度引擎。embedding/llm 模式会优先从环境变量构建 provider。
    """
    mode = mode.lower()
    cfg = config or {}

    if mode == "lexical":
        return LexicalSimilarityEngine(cfg)
    if mode == "embedding":
        if "embedding_function" not in cfg:
            emb_fn = _build_embedding_from_config()
            if emb_fn:
                cfg = {**cfg, "embedding_function": emb_fn}
        return EmbeddingSimilarityEngine(cfg)
    if mode == "llm":
        if "llm_client" not in cfg:
            llm_fn = _build_llm_from_config()
            if llm_fn:
                cfg = {**cfg, "llm_client": llm_fn}
        return LLMSimilarityEngine(cfg)
    raise ValueError(f"Unknown similarity mode: {mode}. Supported: lexical, embedding, llm")


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

