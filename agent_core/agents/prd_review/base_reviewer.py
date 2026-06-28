from dataclasses import dataclass, field

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from agent_core.agents.prd_review.context_builder import (
    PrdReviewChunk,
    PrdReviewDocumentContext,
)
from agent_core.common.llm_result_validate_util import (
    clean_llm_json_content,
    extract_llm_content,
)
from agent_core.models.prd.prd_review_models import (
    PrdReviewDimension,
    PrdReviewError,
    PrdReviewIssue,
    PrdReviewerResponse,
)
from agent_core.prompts.prd.prd_review_prompts import (
    PRD_REVIEW_REPAIR_PROMPT,
    PRD_REVIEW_USER_PROMPT,
)


@dataclass
class ReviewerExecutionResult:
    issues: list[PrdReviewIssue] = field(default_factory=list)
    errors: list[PrdReviewError] = field(default_factory=list)
    llm_call_count: int = 0
    successful_chunk_count: int = 0


class BasePrdReviewer:
    """三个 PRD Reviewer 共用的 LLM 调用和证据校验流程。"""

    reviewer_name: str
    dimension: PrdReviewDimension
    system_prompt: str

    def __init__(self, llm: BaseChatModel) -> None:
        self.llm = llm

    def review(
        self,
        context: PrdReviewDocumentContext,
    ) -> ReviewerExecutionResult:
        execution = ReviewerExecutionResult()
        for chunk in context.chunks:
            issues, errors, call_count = self._review_chunk(
                context,
                chunk,
            )
            execution.issues.extend(issues)
            execution.errors.extend(errors)
            execution.llm_call_count += call_count
            if not errors:
                execution.successful_chunk_count += 1
        execution.issues = list({
            issue.issue_id: issue for issue in execution.issues
        }.values())
        return execution

    def _review_chunk(
        self,
        context: PrdReviewDocumentContext,
        chunk: PrdReviewChunk,
    ) -> tuple[list[PrdReviewIssue], list[PrdReviewError], int]:
        call_count = 1
        try:
            invalid_output = self._invoke_review(context, chunk)
        except Exception as invoke_error:
            return (
                [],
                [PrdReviewError(
                    reviewer=self.reviewer_name,
                    chunk_id=chunk.chunk_id,
                    message=(
                        "LLM 调用失败："
                        f"{self._describe_exception(invoke_error)}"
                    ),
                )],
                call_count,
            )

        try:
            return self._parse_and_validate(invalid_output, chunk), [], call_count
        except Exception as first_error:
            try:
                call_count += 1
                repaired_output = self._invoke_repair(
                    chunk=chunk,
                    error=str(first_error),
                    invalid_output=invalid_output,
                )
                return (
                    self._parse_and_validate(repaired_output, chunk),
                    [],
                    call_count,
                )
            except Exception as repair_error:
                return (
                    [],
                    [PrdReviewError(
                        reviewer=self.reviewer_name,
                        chunk_id=chunk.chunk_id,
                        message=(
                            "LLM 输出修复失败；"
                            f"首次错误：{self._describe_exception(first_error)}；"
                            f"修复错误：{self._describe_exception(repair_error)}"
                        ),
                    )],
                    call_count,
                )

    def _invoke_review(
        self,
        context: PrdReviewDocumentContext,
        chunk: PrdReviewChunk,
    ) -> str:
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt),
            ("user", PRD_REVIEW_USER_PROMPT),
        ])
        messages = prompt.format_messages(
            document_outline=context.document_outline,
            semantic_index=context.semantic_index,
            chunk_content=chunk.content,
        )
        result = self.llm.invoke(messages)
        return extract_llm_content(result)

    def _invoke_repair(
        self,
        *,
        chunk: PrdReviewChunk,
        error: str,
        invalid_output: str,
    ) -> str:
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt),
            ("user", PRD_REVIEW_REPAIR_PROMPT),
        ])
        messages = prompt.format_messages(
            error=error,
            invalid_output=invalid_output,
            chunk_content=chunk.content,
        )
        result = self.llm.invoke(messages)
        return extract_llm_content(result)

    def _parse_and_validate(
        self,
        result: str,
        chunk: PrdReviewChunk,
    ) -> list[PrdReviewIssue]:
        try:
            response = PrdReviewerResponse.model_validate_json(
                clean_llm_json_content(result)
            )
        except (ValidationError, ValueError) as exc:
            raise ValueError(f"LLM 返回 JSON 不符合评审模型：{exc}") from exc

        issues: list[PrdReviewIssue] = []
        for candidate in response.issues:
            if candidate.dimension != self.dimension:
                raise ValueError(
                    f"维度必须为 {self.dimension.value}，"
                    f"实际为 {candidate.dimension.value}"
                )
            source_at_location = chunk.location_texts.get(
                candidate.location
            )
            if source_at_location is None:
                raise ValueError(
                    f"location 不在当前片段：{candidate.location}"
                )
            if self._normalize(candidate.source_text) not in self._normalize(
                source_at_location
            ):
                raise ValueError(
                    "source_text 不是 location 对应节点中的连续原文："
                    f"{candidate.source_text}"
                )
            issues.append(PrdReviewIssue.from_candidate(candidate))
        return issues

    @staticmethod
    def _normalize(value: str) -> str:
        return "".join(value.split())

    @staticmethod
    def _describe_exception(exc: Exception) -> str:
        status_code = getattr(exc, "status_code", None)
        message = " ".join(str(exc).split())
        if "<!doctypehtml" in message.lower() or "<html" in message.lower():
            return (
                f"{type(exc).__name__}"
                f"{f'（HTTP {status_code}）' if status_code else ''}: "
                "上游模型网关返回 HTML 拦截页，请检查 LLM_BASE_URL、"
                "网络权限和网关策略"
            )
        if len(message) > 500:
            message = message[:500] + "..."
        return f"{type(exc).__name__}: {message}"
