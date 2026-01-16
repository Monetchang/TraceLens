"""
Similarity Engine 抽象基类
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict


class SimilarityEngine(ABC):
    """相似度计算引擎抽象基类"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化相似度引擎
        
        Args:
            config: 引擎配置参数
        """
        self.config = config or {}
    
    @abstractmethod
    def compute(
        self,
        source_text: str,
        target_text: str,
        *,
        context: Optional[Dict] = None
    ) -> float:
        """
        计算两个文本的相似度
        
        Args:
            source_text: 源文本
            target_text: 目标文本
            context: 可选的上下文信息（如 query, answer 等）
            
        Returns:
            相似度分数，范围 [0.0, 1.0]
        """
        pass
    
    def get_mode(self) -> str:
        """返回当前引擎的模式名称"""
        return self.__class__.__name__.replace("SimilarityEngine", "").lower()

