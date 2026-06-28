from enum import Enum
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field


class PrdReviewDimension(str, Enum):
    AMBIGUITY = "ambiguity"
    LOGIC_CLOSURE = "logic_closure"
    BOUNDARY_VALUE = "boundary_value"


class PrdReviewSeverity(str, Enum):
    BLOCKER = "blocker"
    MAJOR = "major"
    MINOR = "minor"
    SUGGESTION = "suggestion"


class PrdReviewStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


class PrdReviewCandidate(BaseModel):
    """LLM 返回且尚未生成稳定 ID 的评审候选项。"""

    model_config = ConfigDict(extra="forbid")

    dimension: PrdReviewDimension
    severity: PrdReviewSeverity
    source_text: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
    location: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class PrdReviewerResponse(BaseModel):
    """单次 Reviewer LLM 调用的严格 JSON 响应。"""

    model_config = ConfigDict(extra="forbid")

    issues: list[PrdReviewCandidate] = Field(default_factory=list)


class PrdReviewIssue(BaseModel):
    """最终对外输出的一条 PRD 评审问题。"""

    model_config = ConfigDict(extra="forbid")

    issue_id: str
    dimension: PrdReviewDimension
    severity: PrdReviewSeverity
    source_text: str
    reason: str
    suggestion: str
    location: str
    confidence: float = Field(ge=0, le=1)

    @classmethod
    def from_candidate(
        cls,
        candidate: PrdReviewCandidate,
    ) -> "PrdReviewIssue":
        normalized_source = " ".join(candidate.source_text.split())
        raw_id = "|".join((
            candidate.dimension.value,
            candidate.location,
            normalized_source,
            candidate.reason,
        ))
        issue_id = f"prd-review-{sha256(raw_id.encode('utf-8')).hexdigest()[:16]}"
        return cls(
            issue_id=issue_id,
            **candidate.model_dump(),
        )


class PrdReviewError(BaseModel):
    """不中断整体评审的 Reviewer 级错误。"""

    model_config = ConfigDict(extra="forbid")

    reviewer: str
    chunk_id: str
    message: str


class PrdReviewReport(BaseModel):
    """PRD 自动评审 Agent 的结构化报告。"""

    model_config = ConfigDict(extra="forbid")

    source_path: str
    status: PrdReviewStatus
    issues: list[PrdReviewIssue] = Field(default_factory=list)
    dimension_counts: dict[PrdReviewDimension, int] = Field(
        default_factory=dict,
    )
    errors: list[PrdReviewError] = Field(default_factory=list)
    reviewed_chunk_count: int = 0
    llm_call_count: int = 0

