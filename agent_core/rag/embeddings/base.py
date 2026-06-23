from abc import ABC, abstractmethod


class BaseEmbedding(ABC):
    """将文本转换为向量的统一抽象接口。"""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """生成单条检索文本的向量。"""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量生成待存储文档的向量。"""
