from langchain_core.language_models import BaseChatModel

from agent_core.agents.prd_review.agent import PrdReviewAgent
from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_review_agent_input import PrdReviewAgentInput
from agent_core.models.prd.prd_review_agent_result import PrdReviewAgentResult


def prd_review_flow(
    prd_file_path: str,
    md_node: MdNode | None = None,
    *,
    use_cleaning_pipeline: bool = True,
    max_chunk_chars: int = 24_000,
    llm: BaseChatModel | None = None,
) -> PrdReviewAgentResult:
    """执行 PRD 自动评审的便捷函数入口。"""

    agent = PrdReviewAgent(llm=llm)
    if md_node is not None:
        return agent.review_node(
            md_node,
            source_path=prd_file_path,
            max_chunk_chars=max_chunk_chars,
        )
    return agent.run(
        PrdReviewAgentInput(
            input_path=prd_file_path,
            use_cleaning_pipeline=use_cleaning_pipeline,
            max_chunk_chars=max_chunk_chars,
        )
    )
