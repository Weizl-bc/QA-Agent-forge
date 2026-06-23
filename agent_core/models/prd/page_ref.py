from dataclasses import field

from pydantic import BaseModel


class PageRef(BaseModel):
    page_id: int
    page_name: str
    relation_type: str  # primary、related、source、target
    confidence: float
    matched_by: list[str] = field(default_factory=list)