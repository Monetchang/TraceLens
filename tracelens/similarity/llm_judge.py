"""
LLM Judge Similarity Engine
基于 LLM 的相似度判断
"""
import re
from typing import Optional, Dict, Callable
from .base import SimilarityEngine


class LLMSimilarityEngine(SimilarityEngine):
    """
    LLM 相似度引擎
    
    需要配置 llm_client
    """
    
    # Prompt 模板
    QUERY_CHUNK_PROMPT = """Please evaluate the semantic relevance between the query and the chunk on a scale of 0 to 1.

Query: {query}

Chunk: {chunk}

Provide a relevance score (0.0 to 1.0) where:
- 0.0: Completely irrelevant
- 0.5: Partially relevant
- 1.0: Highly relevant

Return ONLY a number between 0.0 and 1.0.
Score:"""

    CHUNK_ANSWER_PROMPT = """Please evaluate how well the chunk supports or contributes to the answer on a scale of 0 to 1.

Chunk: {chunk}

Answer: {answer}

Provide a support score (0.0 to 1.0) where:
- 0.0: No support or contribution
- 0.5: Partial support
- 1.0: Strong support

Return ONLY a number between 0.0 and 1.0.
Score:"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.llm_client: Optional[Callable] = config.get("llm_client") if config else None
        self.cache: Dict[str, float] = {}
    
    def set_llm_client(self, client: Callable[[str], str]):
        """设置 LLM client"""
        self.llm_client = client
    
    def compute(
        self,
        source_text: str,
        target_text: str,
        *,
        context: Optional[Dict] = None
    ) -> float:
        """使用 LLM 判断相似度"""
        if not source_text or not target_text:
            return 0.0
        
        if not self.llm_client:
            raise ValueError("LLM client not configured")
        
        context = context or {}
        
        # 根据 context 选择 prompt 模板
        if context.get("type") == "chunk_answer":
            prompt = self.CHUNK_ANSWER_PROMPT.format(
                chunk=source_text,
                answer=target_text
            )
        else:  # 默认是 query_chunk
            prompt = self.QUERY_CHUNK_PROMPT.format(
                query=source_text,
                chunk=target_text
            )
        
        # 缓存 key
        cache_key = f"{source_text[:50]}_{target_text[:50]}_{context.get('type', 'query_chunk')}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # 调用 LLM
            response = self.llm_client(prompt)
            
            # 解析分数
            score = self._parse_score(response)
            
            # 缓存结果
            self.cache[cache_key] = score
            
            return score
        except Exception as e:
            print(f"Warning: LLM judgment failed: {e}")
            return 0.0
    
    def _parse_score(self, response: str) -> float:
        """从 LLM 响应中解析分数"""
        # 尝试提取数字
        numbers = re.findall(r'0?\.\d+|[01]\.?\d*', response)
        
        if not numbers:
            return 0.0
        
        try:
            score = float(numbers[0])
            # 确保在 [0, 1] 范围内
            return max(0.0, min(1.0, score))
        except ValueError:
            return 0.0

