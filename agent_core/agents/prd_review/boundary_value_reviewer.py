from agent_core.agents.prd_review.base_reviewer import BasePrdReviewer
from agent_core.models.prd.prd_review_models import PrdReviewDimension
from agent_core.prompts.prd.prd_review_prompts import (
    BOUNDARY_VALUE_REVIEW_SYSTEM_PROMPT,
)


class BoundaryValueReviewer(BasePrdReviewer):
    """通过 LLM 判断范围、限制和校验场景的边界规则是否完整。"""

    reviewer_name = "BoundaryValueReviewer"
    dimension = PrdReviewDimension.BOUNDARY_VALUE
    system_prompt = BOUNDARY_VALUE_REVIEW_SYSTEM_PROMPT

