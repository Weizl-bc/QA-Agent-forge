from pydantic import BaseModel, Field


class PageRef(BaseModel):
    page_id: str  # 页面唯一标识
    system_name: str = ""  # 页面所属系统
    page_name: str  # 页面名称
    relation_type: str  # 页面与当前需求节点的关系类型：primary、related、source、target
    confidence: float  # 页面关联匹配的置信度
    matched_by: list[str] = Field(default_factory=list)  # 页面关联命中的匹配依据
