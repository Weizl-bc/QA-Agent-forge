from abc import ABC, abstractmethod
from typing import Any


VectorRecord = dict[str, Any]
VectorStoreResult = dict[str, Any]


class BaseVectorStore(ABC):
    """向量数据存储与检索操作的统一抽象接口。"""

    @abstractmethod
    def create_collection(
        self,
        collection_name: str,
        dimension: int,
        *,
        primary_field_name: str = "id",
        vector_field_name: str = "vector",
        metric_type: str = "COSINE",
        auto_id: bool = False,
    ) -> None:
        """创建向量集合；集合已存在时不重复创建。"""

    @abstractmethod
    def has_collection(self, collection_name: str) -> bool:
        """判断向量集合是否存在。"""

    @abstractmethod
    def list_collections(self) -> list[str]:
        """返回所有向量集合名称。"""

    @abstractmethod
    def drop_collection(self, collection_name: str) -> None:
        """删除向量集合；集合不存在时不报错。"""

    @abstractmethod
    def insert(
        self,
        collection_name: str,
        records: list[VectorRecord],
    ) -> VectorStoreResult:
        """插入向量及其元数据。"""

    @abstractmethod
    def upsert(
        self,
        collection_name: str,
        records: list[VectorRecord],
    ) -> VectorStoreResult:
        """根据主键新增或更新向量及其元数据。"""

    @abstractmethod
    def search(
        self,
        collection_name: str,
        vectors: list[list[float]],
        *,
        limit: int = 10,
        filter_expression: str = "",
        output_fields: list[str] | None = None,
        search_params: dict[str, Any] | None = None,
    ) -> list[list[VectorStoreResult]]:
        """执行向量相似度搜索。"""

    @abstractmethod
    def query(
        self,
        collection_name: str,
        *,
        filter_expression: str = "",
        ids: list[int | str] | int | str | None = None,
        output_fields: list[str] | None = None,
    ) -> list[VectorStoreResult]:
        """按照主键或过滤表达式读取向量记录。"""

    @abstractmethod
    def delete(
        self,
        collection_name: str,
        *,
        ids: list[int | str] | int | str | None = None,
        filter_expression: str | None = None,
    ) -> VectorStoreResult:
        """按照主键或过滤表达式删除记录。"""

    @abstractmethod
    def close(self) -> None:
        """释放向量存储客户端资源。"""
