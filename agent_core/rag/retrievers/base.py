from abc import ABC, abstractmethod
from typing import Any


RetrievalResult = dict[str, Any]


class BaseRetriever(ABC):
    """根据自然语言查询召回相关向量记录。"""

    @abstractmethod
    def retrieve(
        self,
        query_text: str,
        *,
        limit: int = 10,
        filter_expression: str = "",
        output_fields: list[str] | None = None,
    ) -> list[RetrievalResult]:
        """向量化查询文本并返回相关记录。"""
