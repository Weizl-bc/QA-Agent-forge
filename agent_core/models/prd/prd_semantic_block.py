from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class PrdSemanticBlock(BaseModel):
    """
        语义块
    """

    model_config = ConfigDict(extra="forbid") # 严格模式，防止LLM幻觉乱填字段

    # 原始文本
    raw_text: str

    # 语义类型
    block_type: str = "unknown"

    # 条件
    conditions: list[str] = Field(default_factory=list)

    # 动作
    actions: list[str] = Field(default_factory=list)

    # 约束
    constraints: list[str] = Field(default_factory=list)

    # 实体
    entities: list[str] = Field(default_factory=list)

    # 是否噪声
    is_noise: bool = False

    # 来源
    source_node_path: Optional[str] = None
    source_title: Optional[str] = None

    # embedding（后置生成）
    embedding: Optional[list[float]] = None