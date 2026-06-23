from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class PrdSemanticBlockType:
    SECTION = "section"           # 普通章节
    REQUIREMENT = "requirement"   # 需求描述
    RULE = "rule"                 # 业务规则
    API = "api"                   # 接口说明
    UI = "ui"                     # 页面/交互说明
    FLOW = "flow"                 # 流程说明
    STATE = "state"               # 状态流转
    DATA = "data"                 # 字段/数据规则
    PERMISSION = "permission"     # 权限规则
    EXCEPTION = "exception"       # 异常规则
    UNKNOWN = "unknown"

class PrdSemanticBlock(BaseModel):
    """
        语义块
    """

    model_config = ConfigDict(extra="forbid") # 严格模式，防止LLM幻觉乱填字段

    raw_text: str   # 原始文本
    block_type: str = "unknown"  # 语义类型
    source_type: str = "content" # 枚举：content、image、table
    conditions: list[str] = Field(default_factory=list)     # 条件
    actions: list[str] = Field(default_factory=list)        # 动作
    constraints: list[str] = Field(default_factory=list)    # 约束
    entities: list[str] = Field(default_factory=list)       # 实体
    is_noise: bool = False  # 是否噪声
    source_node_path: Optional[str] = None  # 来源
    source_title: Optional[str] = None
    source_image_id: Optional[str] = None
    embedding: Optional[list[float]] = None  # embedding（后置生成）
