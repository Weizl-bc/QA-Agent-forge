from collections.abc import Callable
from pathlib import Path

from langchain_core.language_models import BaseChatModel

from agent_core.Infrastructure.prd.standardization_prd_md import (
    standardization_prd_md_with_business_structure,
)
from agent_core.agents import BaseAgent
from agent_core.agents.prd_review.ambiguity_reviewer import (
    AmbiguityReviewer,
)
from agent_core.agents.prd_review.boundary_value_reviewer import (
    BoundaryValueReviewer,
)
from agent_core.agents.prd_review.context_builder import (
    PrdReviewContextBuilder,
)
from agent_core.agents.prd_review.logic_closure_reviewer import (
    LogicClosureReviewer,
)
from agent_core.common.json_utils import json_to_model
from agent_core.llm.base import create_model
from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_review_agent_input import PrdReviewAgentInput
from agent_core.models.prd.prd_review_agent_result import PrdReviewAgentResult
from agent_core.models.prd.prd_review_models import (
    PrdReviewDimension,
    PrdReviewError,
    PrdReviewStatus,
)
from agent_core.workflows.prd_cleaning_pipeline import PrdCleaningPipeline


class PrdReviewAgent(BaseAgent[PrdReviewAgentInput, PrdReviewAgentResult]):
    """编排 PRD 上下文构建和三个 LLM Reviewer。"""

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        model_factory: Callable[[], BaseChatModel] | None = None,
    ) -> None:
        self._llm = llm
        self._model_factory = model_factory

    def run(self, input_data: PrdReviewAgentInput) -> PrdReviewAgentResult:
        try:
            if input_data.read_local_json:
                json_content = Path(input_data.input_path).read_text(
                    encoding="utf-8"
                )
                root = json_to_model(json_content, MdNode)
            elif input_data.use_cleaning_pipeline:
                root = PrdCleaningPipeline().run(input_data.input_path).root
            else:
                root = standardization_prd_md_with_business_structure(
                    input_data.input_path
                )
        except Exception as exc:
            return self._failed_report(
                source_path=input_data.input_path,
                message=(
                    "PRD 读取或解析失败："
                    f"{self._describe_exception(exc)}"
                ),
            )

        return self.review_node(
            root,
            source_path=input_data.input_path,
            max_chunk_chars=input_data.max_chunk_chars,
        )

    def review_node(
        self,
        root: MdNode,
        *,
        source_path: str = "",
        max_chunk_chars: int = 24_000,
    ) -> PrdReviewAgentResult:
        try:
            context = PrdReviewContextBuilder(
                max_chunk_chars=max_chunk_chars
            ).build(root)
        except Exception as exc:
            return self._failed_report(
                source_path=source_path,
                message=(
                    "评审上下文构建失败："
                    f"{self._describe_exception(exc)}"
                ),
            )

        try:
            llm = self._llm or (
                self._model_factory()
                if self._model_factory is not None
                else create_model(temperature=0)
            )
        except Exception as exc:
            return self._failed_report(
                source_path=source_path,
                message=f"LLM 初始化失败：{self._describe_exception(exc)}",
                reviewed_chunk_count=len(context.chunks),
            )

        issues = []
        errors: list[PrdReviewError] = []
        llm_call_count = 0
        successful_chunk_count = 0
        reviewers = (
            AmbiguityReviewer(llm),
            LogicClosureReviewer(llm),
            BoundaryValueReviewer(llm),
        )
        for reviewer in reviewers:
            execution = reviewer.review(context)
            issues.extend(execution.issues)
            errors.extend(execution.errors)
            llm_call_count += execution.llm_call_count
            successful_chunk_count += execution.successful_chunk_count

        unique_issues = list({
            issue.issue_id: issue for issue in issues
        }.values())
        unique_issues.sort(key=lambda issue: (
            self._severity_order(issue.severity.value),
            issue.dimension.value,
            issue.location,
            issue.issue_id,
        ))
        dimension_counts = {
            dimension: sum(
                issue.dimension == dimension for issue in unique_issues
            )
            for dimension in PrdReviewDimension
        }
        status = (
            PrdReviewStatus.SUCCESS
            if not errors
            else (
                PrdReviewStatus.PARTIAL_FAILURE
                if successful_chunk_count
                else PrdReviewStatus.FAILED
            )
        )
        return PrdReviewAgentResult(
            source_path=source_path,
            status=status,
            issues=unique_issues,
            dimension_counts=dimension_counts,
            errors=errors,
            reviewed_chunk_count=len(context.chunks),
            llm_call_count=llm_call_count,
        )

    @staticmethod
    def _severity_order(severity: str) -> int:
        return {
            "blocker": 0,
            "major": 1,
            "minor": 2,
            "suggestion": 3,
        }[severity]

    @staticmethod
    def _failed_report(
        *,
        source_path: str,
        message: str,
        reviewed_chunk_count: int = 0,
    ) -> PrdReviewAgentResult:
        return PrdReviewAgentResult(
            source_path=source_path,
            status=PrdReviewStatus.FAILED,
            issues=[],
            dimension_counts={
                dimension: 0 for dimension in PrdReviewDimension
            },
            errors=[PrdReviewError(
                reviewer="PrdReviewAgent",
                chunk_id="initialization",
                message=message,
            )],
            reviewed_chunk_count=reviewed_chunk_count,
            llm_call_count=0,
        )

    @staticmethod
    def _describe_exception(exc: Exception) -> str:
        status_code = getattr(exc, "status_code", None)
        message = " ".join(str(exc).split())
        if "<!doctypehtml" in message.lower() or "<html" in message.lower():
            return (
                f"{type(exc).__name__}"
                f"{f'（HTTP {status_code}）' if status_code else ''}: "
                "上游模型网关返回 HTML 拦截页，请检查模型网关配置和网络权限"
            )
        if len(message) > 500:
            message = message[:500] + "..."
        return f"{type(exc).__name__}: {message}"


# 兼容早期拼写。
PrdPreviewAgent = PrdReviewAgent
