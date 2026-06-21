from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from agent_core.models.prd.prd_semantic_block import PrdSemanticBlock


class OcrText(BaseModel):
    text: str = ""
    confidence: str = "medium"


class ImageAnalysisResult(BaseModel):
    """
    第一个 Prompt 的输出结果：
    图片 -> 图片结构化分析
    """

    model_config = ConfigDict(extra="forbid")

    image_type: str = "unknown"
    is_business_relevant: bool = True
    is_noise: bool = False

    ocr_texts: list[OcrText] = Field(default_factory=list)
    participants: list[dict] = Field(default_factory=list)
    lanes: list[dict] = Field(default_factory=list)
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)
    branches: list[dict] = Field(default_factory=list)
    business_rules: list[dict] = Field(default_factory=list)

    business_summary: str = ""
    uncertain_items: list[str] = Field(default_factory=list)


class ImageSemanticBlockResult(BaseModel):
    """
    第二个 Prompt 的输出结果：
    图片结构化分析 -> PrdSemanticBlock
    """

    model_config = ConfigDict(extra="forbid")

    semantic_blocks: list[PrdSemanticBlock] = Field(default_factory=list)
    test_points: list[dict] = Field(default_factory=list)
    uncertain_items: list[str] = Field(default_factory=list)