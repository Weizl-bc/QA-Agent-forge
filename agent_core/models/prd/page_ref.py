from typing import Literal

from pydantic import BaseModel, Field


class PageRef(BaseModel):
    """PRD 节点关联的页面及其所属系统快照。"""

    page_id: int
    page_code: str
    page_name: str
    page_path: str | None = None
    system_id: int
    system_code: str | None = None
    system_name: str
    relation_type: Literal["primary", "related", "source", "target"]
    confidence: float
    matched_by: list[str] = Field(default_factory=list)
