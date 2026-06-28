from pydantic import BaseModel, Field


class PrdReviewAgentInput(BaseModel):
    """PRD Review Agent 的文件输入配置。"""

    input_path: str
    read_local_json: bool = False
    use_cleaning_pipeline: bool = True
    max_chunk_chars: int = Field(default=24_000, ge=1)
