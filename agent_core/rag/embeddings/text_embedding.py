from langchain_core.embeddings import Embeddings

from agent_core.llm.base import create_embedding_model
from agent_core.rag.embeddings.base import BaseEmbedding


class TextEmbedding(BaseEmbedding):
    """使用项目已配置的文本向量模型生成 embedding。"""

    def __init__(self, model: Embeddings | None = None) -> None:
        self.model = model or create_embedding_model()

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("待向量化的查询文本不能为空")
        return self.model.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not text.strip() for text in texts):
            raise ValueError("待向量化的文档文本不能为空")
        return self.model.embed_documents(texts)
