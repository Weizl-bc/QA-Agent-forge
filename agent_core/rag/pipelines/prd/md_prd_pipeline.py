from agent_core.Infrastructure.prd.rag_pre_processor import rag_pre_processor
from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_pipeline_context import PrdPipelineContext
from agent_core.rag.embeddings import TextEmbedding
from agent_core.rag.embeddings.base import BaseEmbedding
from agent_core.rag.pipelines.base import BasePipeline
from agent_core.rag.vectorstores import MilvusLiteVectorStore
from agent_core.rag.vectorstores.base import BaseVectorStore, VectorStoreResult


class MDPRDPipeline(BasePipeline):
    """将清洗后的 MdNode 树转换为向量记录并写入向量库。"""

    def __init__(
        self,
        collection_name: str = "prd_knowledge",
        *,
        document_id: str | None = None,
        embedding: BaseEmbedding | None = None,
        vector_store: BaseVectorStore | None = None,
    ) -> None:
        self.collection_name = collection_name
        self.document_id = document_id
        self.embedding = embedding or TextEmbedding()
        self.vector_store = vector_store or MilvusLiteVectorStore()

    def run(
        self,
        value: MdNode | PrdPipelineContext,
    ) -> VectorStoreResult:
        """预处理 PRD、生成 embedding，并以主键幂等写入向量库。"""
        root = value.root if isinstance(value, PrdPipelineContext) else value
        if not isinstance(root, MdNode):
            raise TypeError("MDPRDPipeline.run 仅支持 MdNode 或 PrdPipelineContext")

        records = rag_pre_processor(
            root,
            document_id=self.document_id,
        )
        if not records:
            return {"upsert_count": 0, "ids": []}

        vectors = self.embedding.embed_documents(
            [record.text for record in records]
        )
        if len(vectors) != len(records):
            raise ValueError("embedding 返回的向量数量与 PRD 记录数量不一致")
        if not vectors or not vectors[0]:
            raise ValueError("embedding 返回了空向量")

        dimension = len(vectors[0])
        if any(len(vector) != dimension for vector in vectors):
            raise ValueError("embedding 返回的向量维度不一致")

        for record, vector in zip(records, vectors, strict=True):
            record.vector = vector

        self.vector_store.create_collection(
            collection_name=self.collection_name,
            dimension=dimension,
            id_type="string",
            metric_type="COSINE",
            auto_id=False,
        )
        return self.vector_store.upsert(
            self.collection_name,
            [record.model_dump() for record in records],
        )
