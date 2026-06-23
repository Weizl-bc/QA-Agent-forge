from pathlib import Path
from typing import Any

from pymilvus import MilvusClient

from agent_core.common.env_config import get_env
from agent_core.rag.vectorstores.base import (
    BaseVectorStore,
    VectorRecord,
    VectorStoreResult,
)


DEFAULT_MILVUS_LITE_DB_PATH = "../vectorstores/milvus_demo_lite.db"


class MilvusLiteVectorStore(BaseVectorStore):
    """基于本地 Milvus Lite 数据库的向量存储实现。"""

    def __init__(self, db_path: str | Path | None = None) -> None:
        configured_path = db_path or get_env(
            "MILVUS_LITE_DB_PATH",
            DEFAULT_MILVUS_LITE_DB_PATH,
        )
        self.db_path = Path(
            configured_path or DEFAULT_MILVUS_LITE_DB_PATH
        ).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.client = MilvusClient(str(self.db_path))

    def create_collection(
        self,
        collection_name: str,
        dimension: int,
        *,
        primary_field_name: str = "id",
        id_type: str = "int",
        vector_field_name: str = "vector",
        metric_type: str = "COSINE",
        auto_id: bool = False,
    ) -> None:
        if self.has_collection(collection_name):
            return
        self.client.create_collection(
            collection_name=collection_name,
            dimension=dimension,
            primary_field_name=primary_field_name,
            id_type=id_type,
            vector_field_name=vector_field_name,
            metric_type=metric_type,
            auto_id=auto_id,
        )

    def has_collection(self, collection_name: str) -> bool:
        return bool(self.client.has_collection(collection_name))

    def list_collections(self) -> list[str]:
        return list(self.client.list_collections())

    def drop_collection(self, collection_name: str) -> None:
        if self.has_collection(collection_name):
            self.client.drop_collection(collection_name)

    def insert(
        self,
        collection_name: str,
        records: list[VectorRecord],
    ) -> VectorStoreResult:
        if not records:
            return {"insert_count": 0, "ids": []}
        return dict(
            self.client.insert(collection_name=collection_name, data=records)
        )

    def upsert(
        self,
        collection_name: str,
        records: list[VectorRecord],
    ) -> VectorStoreResult:
        if not records:
            return {"upsert_count": 0, "ids": []}
        return dict(
            self.client.upsert(collection_name=collection_name, data=records)
        )

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
        if not vectors:
            return []
        return self.client.search(
            collection_name=collection_name,
            data=vectors,
            limit=limit,
            filter=filter_expression,
            output_fields=output_fields,
            search_params=search_params,
        )

    def query(
        self,
        collection_name: str,
        *,
        filter_expression: str = "",
        ids: list[int | str] | int | str | None = None,
        output_fields: list[str] | None = None,
    ) -> list[VectorStoreResult]:
        return self.client.query(
            collection_name=collection_name,
            filter=filter_expression,
            ids=ids,
            output_fields=output_fields,
        )

    def delete(
        self,
        collection_name: str,
        *,
        ids: list[int | str] | int | str | None = None,
        filter_expression: str | None = None,
    ) -> VectorStoreResult:
        if ids is None and not filter_expression:
            raise ValueError("删除向量时必须提供 ids 或 filter_expression")
        result = self.client.delete(
            collection_name=collection_name,
            ids=ids,
            filter=filter_expression,
        )
        if isinstance(result, dict):
            return dict(result)
        deleted_ids = list(result)
        return {"delete_count": len(deleted_ids), "ids": deleted_ids}

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "MilvusLiteVectorStore":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> None:
        self.close()
