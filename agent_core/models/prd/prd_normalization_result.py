from pydantic import BaseModel, ConfigDict, Field


class PrdNormalizationResult(BaseModel):
    """PRD 节点正文标准化及可检索性判断结果。"""

    model_config = ConfigDict(extra="forbid")

    normalized_content: str = Field(
        description="基于节点标题和原始正文生成的标准化纯文本",
    )
    is_retrievable: bool = Field(
        description="当前节点是否包含可用于需求检索、评审或测试设计的业务信息",
    )
    retrieval_reason: str = Field(
        description="模型判定当前节点是否可检索的简要依据",
    )
