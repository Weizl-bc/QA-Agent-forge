from pydantic import BaseModel, Field


class PrdVectorRecord(BaseModel):
    """PRD 节点经过切分后写入向量库的单条记录。"""

    id: str = Field(description="向量记录的唯一主键，用于幂等 upsert")
    vector: list[float] = Field(
        default_factory=list,
        description="由 embedding 模型生成的文本向量",
    )
    text: str = Field(description="用于生成向量并在召回后返回的完整检索文本")
    document_id: str = Field(description="当前记录所属 PRD 文档的唯一标识")
    node_id: str = Field(description="当前记录来源 MdNode 的唯一标识")
    node_path: str = Field(description="当前节点在 PRD 标题树中的完整路径")
    title: str = Field(description="当前记录来源节点的标题")
    node_level: int = Field(description="当前记录来源节点的 Markdown 标题层级")
    node_type: str = Field(description="当前记录来源节点的业务类型")
    source_path: str = Field(description="当前记录来源 PRD 文件的路径")
    block_index: int = Field(description="语义块在当前节点中的顺序编号")
    block_type: str = Field(description="当前语义块的业务语义类型")
    source_type: str = Field(description="语义内容的来源类型，例如 content、image 或 table")
    conditions: list[str] = Field(
        default_factory=list,
        description="当前语义块生效所需满足的条件",
    )
    actions: list[str] = Field(
        default_factory=list,
        description="当前语义块描述的用户动作或系统动作",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="当前语义块包含的业务限制和约束",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="当前语义块涉及的页面、角色、对象或业务实体",
    )
