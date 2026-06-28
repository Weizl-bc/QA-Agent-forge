from agent_core.agents.prd_review.base_reviewer import BasePrdReviewer
from agent_core.models.prd.prd_review_models import PrdReviewDimension
from agent_core.prompts.prd.prd_review_prompts import (
    LOGIC_CLOSURE_REVIEW_SYSTEM_PROMPT,
)


class LogicClosureReviewer(BasePrdReviewer):
    """通过 LLM 检查业务输入、处理、输出和异常路径是否闭环。"""

    reviewer_name = "LogicClosureReviewer"
    dimension = PrdReviewDimension.LOGIC_CLOSURE
    system_prompt = LOGIC_CLOSURE_REVIEW_SYSTEM_PROMPT

