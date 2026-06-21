from typing import Optional

from pydantic import BaseModel, ConfigDict


class MdImageRef(BaseModel):
    """
    Markdown 图片引用。
    作为 MdNode 的结构化子资源存在。
    """

    model_config = ConfigDict(extra="forbid")
    id: str
    raw_markdown: str = ""
    alt_text: Optional[str] = None
    src: str
    title: str
    local_path: Optional[str] = None
    image_type: str = "unknown"
    ocr_text: str = ""
    visual_summary: str = ""
    is_noise: bool = False
    source_node_id: Optional[str] = None
    source_node_path: Optional[str] = None
    source_title: Optional[str] = None