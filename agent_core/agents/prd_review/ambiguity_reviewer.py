from agent_core.agents.prd_review.base_reviewer import BasePrdReviewer
from agent_core.models.prd.prd_review_models import PrdReviewDimension
from agent_core.prompts.prd.prd_review_prompts import (
    AMBIGUITY_REVIEW_SYSTEM_PROMPT,
)


class AmbiguityReviewer(BasePrdReviewer):
    """通过 LLM 结合上下文判断 PRD 表述是否可执行、可测试。"""

    reviewer_name = "AmbiguityReviewer"
    dimension = PrdReviewDimension.AMBIGUITY
    system_prompt = AMBIGUITY_REVIEW_SYSTEM_PROMPT

