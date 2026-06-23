from typing import Any

from agent_core.rag.embeddings import TextEmbedding
from agent_core.rag.embeddings.base import BaseEmbedding
from agent_core.rag.retrievers.base import BaseRetriever, RetrievalResult
from agent_core.rag.vectorstores import MilvusLiteVectorStore
from agent_core.rag.vectorstores.base import BaseVectorStore


class VectorRetriever(BaseRetriever):
    """组合文本向量模型与向量存储完成自然语言召回。"""

    def __init__(
        self,
        embedding: BaseEmbedding,
        vector_store: BaseVectorStore,
        collection_name: str,
        *,
        search_params: dict[str, Any] | None = None,
    ) -> None:
        self.embedding = embedding
        self.vector_store = vector_store
        self.collection_name = collection_name
        self.search_params = search_params

    def retrieve(
        self,
        query_text: str,
        *,
        limit: int = 10,
        filter_expression: str = "",
        output_fields: list[str] | None = None,
    ) -> list[RetrievalResult]:
        if not query_text.strip():
            raise ValueError("检索文本不能为空")
        if limit < 1:
            raise ValueError("limit 必须大于等于 1")

        query_vector = self.embedding.embed_query(query_text)
        search_results = self.vector_store.search(
            collection_name=self.collection_name,
            vectors=[query_vector],
            limit=limit,
            filter_expression=filter_expression,
            output_fields=output_fields,
            search_params=self.search_params,
        )
        return search_results[0] if search_results else []

if __name__ == "__main__":
    embedding = TextEmbedding()
    vector_store = MilvusLiteVectorStore()

    retriever = VectorRetriever(
        embedding=embedding,
        vector_store=vector_store,
        collection_name="你的集合名称",
    )
    print(retriever.retrieve("IPhone14有哪些颜色"))