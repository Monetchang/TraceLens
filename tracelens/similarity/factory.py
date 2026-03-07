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

_embedding_client = None
_llm_client = None


def _get_embedding_client():
    global _embedding_client
    if _embedding_client is None:
        import httpx
        _embedding_client = httpx.Client(
            timeout=30.0,
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
        )
    return _embedding_client


def _get_llm_client():
    global _llm_client
    if _llm_client is None:
        import httpx
        _llm_client = httpx.Client(
            timeout=60.0,
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
        )
    return _llm_client


def _build_embedding_from_config() -> Optional[Callable]:
    """从环境变量构建 embedding 函数（支持 OpenAI 兼容格式、Ollama、腾讯混元）"""
    from tracelens.config import EMBEDDING_ENDPOINT, EMBEDDING_API_KEY, EMBEDDING_MODEL
    if not EMBEDDING_ENDPOINT:
        return None
    import numpy as np
    headers = {"Authorization": f"Bearer {EMBEDDING_API_KEY}"} if EMBEDDING_API_KEY else {}
    client = _get_embedding_client()

    def _embed(text: str):
        payload = {"input": text}
        if EMBEDDING_MODEL:
            payload["model"] = EMBEDDING_MODEL
        r = client.post(EMBEDDING_ENDPOINT, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        # OpenAI / 阿里云百炼 / DeepSeek / 腾讯混元(OpenAI兼容) 等格式：{"data": [{"embedding": [...]}]}
        if isinstance(data, dict) and "data" in data:
            return np.array(data["data"][0]["embedding"])
        # 腾讯混元原生格式：{"Response": {"Data": [{"Embedding": [...]}]}}
        if isinstance(data, dict) and "Response" in data:
            return np.array(data["Response"]["Data"][0]["Embedding"])
        # Ollama 格式：{"embeddings": [[...]]}
        if isinstance(data, dict) and "embeddings" in data:
            emb = data["embeddings"]
            return np.array(emb[0] if isinstance(emb[0], list) else emb)
        # 纯数组格式
        if isinstance(data, list):
            return np.array(data[0] if isinstance(data[0], list) else data)
        raise ValueError(f"Unrecognized embedding response format: {list(data.keys()) if isinstance(data, dict) else type(data)}")

    return _embed


def _build_llm_from_config() -> Optional[Callable]:
    """从环境变量构建 LLM 客户端（兼容 OpenAI Chat Completions 格式）"""
    from tracelens.config import LLM_ENDPOINT, LLM_API_KEY, LLM_MODEL
    if not LLM_ENDPOINT:
        return None
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"} if LLM_API_KEY else {}
    client = _get_llm_client()

    def _complete(prompt: str) -> str:
        r = client.post(
            LLM_ENDPOINT,
            json={"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}]},
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

