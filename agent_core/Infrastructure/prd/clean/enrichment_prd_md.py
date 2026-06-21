import json
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

import structlog
from langchain_core.prompts import ChatPromptTemplate
from openai import OpenAIError, RateLimitError

from agent_core.common.env_config import get_env
from agent_core.common.llm_result_validate_util import clean_llm_json_content
from agent_core.common.tree_utils import walk_md_tree
from agent_core.llm.base import create_model
from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_semantic_block import PrdSemanticBlock
from agent_core.prompts.prd.enrichment_prd_prompt import (
    ENRICHMENT_SEMANTIC_BLOCK_PROMPT,
    ENRICHMENT_SEMANTIC_BLOCK_USER_PROMPT,
)


logger = structlog.get_logger(__name__)
ENRICHMENT_FIELDS = (
    "actions",
    "conditions",
    "constraints",
    "entities",
)


@dataclass(frozen=True)
class EnrichmentSettings:
    max_workers: int
    min_interval_seconds: float
    max_attempts: int
    backoff_seconds: float
    max_backoff_seconds: float
    jitter_seconds: float


class _SharedRateLimiter:
    """在并发 worker 间共享请求间隔和 429 冷却时间。"""

    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval_seconds = min_interval_seconds
        self._next_request_at = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_request_at - now)
            if delay:
                time.sleep(delay)
            self._next_request_at = (
                time.monotonic() + self._min_interval_seconds
            )

    def defer(self, delay_seconds: float) -> None:
        with self._lock:
            self._next_request_at = max(
                self._next_request_at,
                time.monotonic() + delay_seconds,
            )


def _get_enrichment_settings(
    max_workers: int | None,
) -> EnrichmentSettings:
    resolved_max_workers = (
        max_workers
        if max_workers is not None
        else int(get_env("PRD_ENRICHMENT_MAX_WORKERS", "1"))
    )
    settings = EnrichmentSettings(
        max_workers=resolved_max_workers,
        min_interval_seconds=float(
            get_env("PRD_ENRICHMENT_MIN_INTERVAL_SECONDS", "0.5")
        ),
        max_attempts=int(
            get_env("PRD_ENRICHMENT_MAX_ATTEMPTS", "4")
        ),
        backoff_seconds=float(
            get_env("PRD_ENRICHMENT_BACKOFF_SECONDS", "2")
        ),
        max_backoff_seconds=float(
            get_env("PRD_ENRICHMENT_MAX_BACKOFF_SECONDS", "60")
        ),
        jitter_seconds=float(
            get_env("PRD_ENRICHMENT_JITTER_SECONDS", "0.5")
        ),
    )
    if settings.max_workers < 1:
        raise ValueError("PRD_ENRICHMENT_MAX_WORKERS 必须大于等于 1")
    if settings.min_interval_seconds < 0:
        raise ValueError(
            "PRD_ENRICHMENT_MIN_INTERVAL_SECONDS 必须大于等于 0"
        )
    if settings.max_attempts < 1:
        raise ValueError("PRD_ENRICHMENT_MAX_ATTEMPTS 必须大于等于 1")
    if (
        settings.backoff_seconds < 0
        or settings.max_backoff_seconds < 0
        or settings.jitter_seconds < 0
    ):
        raise ValueError("enrichment 退避时间配置不能为负数")
    return settings


def _parse_enrichment_result(result: Any) -> dict[str, list[str]]:
    content = clean_llm_json_content(result)
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("语义增强结果必须是 JSON 对象")

    parsed: dict[str, list[str]] = {}
    for field_name in ENRICHMENT_FIELDS:
        values = data.get(field_name)
        if (
            not isinstance(values, list)
            or not all(isinstance(item, str) for item in values)
        ):
            raise ValueError(
                f"语义增强字段 {field_name} 必须是字符串数组"
            )
        parsed[field_name] = list(dict.fromkeys(
            item.strip()
            for item in values
            if item.strip()
        ))
    return parsed


def _retry_after_seconds(exc: RateLimitError) -> float | None:
    response = getattr(exc, "response", None)
    if response is None:
        return None
    retry_after = response.headers.get("retry-after")
    if not retry_after:
        return None
    try:
        return max(0.0, float(retry_after))
    except ValueError:
        return None


def _rate_limit_delay(
    attempt: int,
    exc: RateLimitError,
    settings: EnrichmentSettings,
) -> float:
    retry_after = _retry_after_seconds(exc)
    if retry_after is not None:
        return min(retry_after, settings.max_backoff_seconds)

    exponential_delay = settings.backoff_seconds * (2 ** (attempt - 1))
    jitter = random.uniform(0, settings.jitter_seconds)
    return min(
        exponential_delay + jitter,
        settings.max_backoff_seconds,
    )


def _enrichment_semantic_block(
    block: PrdSemanticBlock,
    settings: EnrichmentSettings,
    rate_limiter: _SharedRateLimiter,
) -> bool:
    """
    单次请求提取四类语义。

    只有完整响应解析成功后才原子更新 block，避免失败时覆盖前一阶段结果。
    """
    llm = create_model(temperature=0, max_retries=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", ENRICHMENT_SEMANTIC_BLOCK_PROMPT),
        ("user", ENRICHMENT_SEMANTIC_BLOCK_USER_PROMPT),
    ])
    chain = prompt | llm

    for attempt in range(1, settings.max_attempts + 1):
        rate_limiter.wait()
        try:
            result = chain.invoke({"raw_text": block.raw_text})
            parsed = _parse_enrichment_result(result)
        except RateLimitError as exc:
            delay_seconds = _rate_limit_delay(
                attempt,
                exc,
                settings,
            )
            rate_limiter.defer(delay_seconds)
            if attempt >= settings.max_attempts:
                logger.warning(
                    "semantic_block_enrichment_rate_limited",
                    attempt=attempt,
                    max_attempts=settings.max_attempts,
                    cooldown_seconds=round(delay_seconds, 2),
                    raw_text_length=len(block.raw_text),
                )
                return False

            logger.warning(
                "semantic_block_enrichment_retrying",
                attempt=attempt,
                max_attempts=settings.max_attempts,
                delay_seconds=round(delay_seconds, 2),
                raw_text_length=len(block.raw_text),
            )
            continue
        except (OpenAIError, json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "semantic_block_enrichment_failed",
                error_type=type(exc).__name__,
                error=str(exc),
                raw_text_length=len(block.raw_text),
            )
            return False

        block.actions = parsed["actions"]
        block.conditions = parsed["conditions"]
        block.constraints = parsed["constraints"]
        block.entities = parsed["entities"]
        return True

    return False


def _enrichment_md_node_type(node: MdNode) -> None:
    """
    代码匹配mdNode的类型
    """
    text = f"{node.title}\n{node.normalized_content or node.content}"
    node_type = "unknown"
    if any(k in text for k in ["接口", "API", "入参", "出参", "请求", "响应"]):
        node_type =  "api"

    if any(k in text for k in ["流程", "流转", "步骤", "泳道"]):
        node_type =  "flow"

    if any(k in text for k in ["状态", "状态机", "待审核", "已完成", "已取消"]):
        node_type =  "state"

    if any(k in text for k in ["字段", "枚举", "必填", "取值", "类型"]):
        node_type =  "data"

    if any(k in text for k in ["权限", "角色", "管理员", "可见", "不可见"]):
        node_type =  "permission"

    if any(k in text for k in ["异常", "失败", "错误", "拦截", "提示"]):
        node_type =  "exception"

    if node.references and not node.content.strip() and not node.semantic_blocks:
        node_type = "reference"

    if node.semantic_blocks:
        node_type =  "requirement"

    node.node_type = node_type


def enrichment_prd_md(
    mdNode: MdNode,
    max_workers: int | None = None,
) -> None:
    """
    语义增强。

    每个语义块仅发起一次模型请求，并在所有 worker 间共享限速与 429 退避。
    单个 block 增强失败时保留已有语义，不中断整棵 PRD。
    """
    settings = _get_enrichment_settings(max_workers)
    blocks: list[PrdSemanticBlock] = []

    def handler(node: MdNode) -> None:
        _enrichment_md_node_type(node)
        blocks.extend(node.semantic_blocks)

    walk_md_tree(mdNode, handler)

    if not blocks:
        return

    rate_limiter = _SharedRateLimiter(
        settings.min_interval_seconds
    )
    logger.info(
        "prd_enrichment_started",
        semantic_block_count=len(blocks),
        planned_request_count=len(blocks),
        max_workers=min(settings.max_workers, len(blocks)),
        min_interval_seconds=settings.min_interval_seconds,
    )

    with ThreadPoolExecutor(
        max_workers=min(settings.max_workers, len(blocks)),
        thread_name_prefix="prd-enrichment",
    ) as executor:
        futures = [
            executor.submit(
                _enrichment_semantic_block,
                block,
                settings,
                rate_limiter,
            )
            for block in blocks
        ]
        successful_count = sum(
            1
            for future in futures
            if future.result()
        )

    logger.info(
        "prd_enrichment_completed",
        semantic_block_count=len(blocks),
        successful_count=successful_count,
        failed_count=len(blocks) - successful_count,
    )
