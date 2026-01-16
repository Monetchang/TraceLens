"""
Lexical Similarity Engine
基于词法的相似度计算（默认方案，零配置）
"""
import re
import math
from typing import Set, List, Dict, Optional
from collections import Counter
from .base import SimilarityEngine


class LexicalSimilarityEngine(SimilarityEngine):
    """
    词法相似度引擎
    
    优先级：
    1. TF-IDF + cosine
    2. keyword overlap 兜底
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.use_tfidf = config.get("use_tfidf", True) if config else True
    
    def compute(
        self,
        source_text: str,
        target_text: str,
        *,
        context: Optional[Dict] = None
    ) -> float:
        """计算词法相似度"""
        if not source_text or not target_text:
            return 0.0
        
        if self.use_tfidf:
            return self._tfidf_cosine_similarity(source_text, target_text)
        else:
            return self._keyword_overlap_similarity(source_text, target_text)
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        # 简单的分词：小写化 + 分割非字母数字字符
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens
    
    def _keyword_overlap_similarity(self, text1: str, text2: str) -> float:
        """基于关键词重叠的相似度"""
        tokens1 = set(self._tokenize(text1))
        tokens2 = set(self._tokenize(text2))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        if union == 0:
            return 0.0
        
        # Jaccard 相似度
        return intersection / union
    
    def _tfidf_cosine_similarity(self, text1: str, text2: str) -> float:
        """基于 TF-IDF 的余弦相似度"""
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # 计算词频
        tf1 = Counter(tokens1)
        tf2 = Counter(tokens2)
        
        # 所有唯一词
        all_words = set(tokens1) | set(tokens2)
        
        # 简化的 IDF（文档频率 = 2，因为只有两个文档）
        # IDF = log(N / df)，这里 N=2，df=1或2
        idf = {}
        for word in all_words:
            df = (1 if word in tf1 else 0) + (1 if word in tf2 else 0)
            idf[word] = math.log(2 / df) if df > 0 else 0
        
        # 计算 TF-IDF 向量
        vec1 = [tf1.get(word, 0) * idf[word] for word in all_words]
        vec2 = [tf2.get(word, 0) * idf[word] for word in all_words]
        
        # 余弦相似度
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # 确保在 [0, 1] 范围内
        return max(0.0, min(1.0, similarity))

