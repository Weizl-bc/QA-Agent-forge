import json
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import Any

import structlog
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from agent_core.common.llm_result_validate_util import (
    clean_llm_json_content,
    extract_llm_content,
)
from agent_core.llm.base import create_model
from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_semantic_block import PrdSemanticBlock
from agent_core.prompts.prd.parser_md_prompt import PARSER_MD_TO_NORMAL_TEXT_PROMPT
from agent_core.prompts.prd.senmatic_prompt import MD_NODE_TO_SEMANTIC_PROMPT


logger = structlog.get_logger(__name__)

MAX_SEMANTIC_PARSE_ATTEMPTS = 2


def _parse_semantic_blocks(result: Any) -> list[PrdSemanticBlock]:
    """解析并校验 LLM 返回的语义块数组。"""
    content = clean_llm_json_content(result)
    data = json.loads(content)
    if not isinstance(data, list):
        raise ValueError("LLM 语义提取结果必须是 JSON 数组")

    return [
        PrdSemanticBlock.model_validate(item)
        for item in data
    ]


def _llm_extract_semantic(
    raw_content: str,
    normalized_content: str,
) -> list[PrdSemanticBlock]:
    """
    llm提取语义
    """

    llm = create_model(temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=MD_NODE_TO_SEMANTIC_PROMPT),
        ("user", """
请输出 PrdSemanticBlock JSON 数组。

【原始文本：唯一事实来源】
{raw_content}

【标准化文本：仅用于理解结构】
{normalized_content}

要求：
1. 不得生成原始文本中不存在的需求。
2. 标准化文本与原始文本冲突时，以原始文本为准。
3. raw_text 必须是原始文本中的连续子串。
4. 标准化文本遗漏的信息仍需从原始文本中提取。
        """)
    ])
    result = (prompt | llm).invoke({
        "raw_content": raw_content,
        "normalized_content": normalized_content,
    })

    for attempt in range(1, MAX_SEMANTIC_PARSE_ATTEMPTS + 1):
        try:
            blocks = _parse_semantic_blocks(result)
            for block in blocks:
                block.source_type = "content"
            return blocks
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            response_content = extract_llm_content(result)
            logger.warning(
                "semantic_extraction_parse_failed",
                method="_llm_extract_semantic",
                attempt=attempt,
                max_attempts=MAX_SEMANTIC_PARSE_ATTEMPTS,
                error_type=type(exc).__name__,
                error=str(exc),
                response_length=len(response_content),
            )

            if attempt >= MAX_SEMANTIC_PARSE_ATTEMPTS:
                raise ValueError(
                    "LLM 语义提取结果经过 "
                    f"{MAX_SEMANTIC_PARSE_ATTEMPTS} 次尝试仍无法解析"
                ) from exc

            repair_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=MD_NODE_TO_SEMANTIC_PROMPT),
                ("user", """
以下模型输出无法解析为 PrdSemanticBlock JSON 数组。

【解析错误】
{error}

【错误输出】
{invalid_output}

【原始文本：唯一事实来源】
{raw_content}

请修复格式并重新输出。
要求：
1. 只能输出合法 JSON 数组，不要输出 Markdown 或解释。
2. 每个数组元素必须符合 PrdSemanticBlock 字段结构。
3. 不得新增原始文本中不存在的信息。
                """),
            ])
            result = (repair_prompt | llm).invoke({
                "error": str(exc),
                "invalid_output": response_content,
                "raw_content": raw_content,
            })

    raise RuntimeError("语义提取重试流程异常结束")

def _normalization_tree_content_llm(content: str) -> str:
    """
    将mdNode中的content的不规范的文本统一为文本形式
    """
    llm = create_model(temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", PARSER_MD_TO_NORMAL_TEXT_PROMPT),
        ("human", "请将以下PRD内容标准化为纯文本，不要输出列表或JSON：{content}")
    ])
    chain = prompt | llm
    result = chain.invoke({"content": content})
    return extract_llm_content(result)


def _normalize_and_extract_node(node: MdNode) -> None:
    """依次完成单个节点的正文标准化和语义抽取。"""
    node_logger = logger.bind(
        node_id=node.id,
        node_title=node.title,
        content_length=len(node.content),
    )
    node_started_at = perf_counter()
    normalization_started_at = perf_counter()
    node_logger.info("semantic_node_normalization_started")

    try:
        node.normalized_content = _normalization_tree_content_llm(node.content)
    except Exception as exc:
        node_logger.exception(
            "semantic_node_normalization_failed",
            duration_ms=round(
                (perf_counter() - normalization_started_at) * 1000,
                2,
            ),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    node_logger.info(
        "semantic_node_normalization_completed",
        duration_ms=round(
            (perf_counter() - normalization_started_at) * 1000,
            2,
        ),
        normalized_content_length=len(node.normalized_content),
    )

    extraction_started_at = perf_counter()
    node_logger.info("semantic_node_extraction_started")
    try:
        node.semantic_blocks = _llm_extract_semantic(
            normalized_content=node.normalized_content,
            raw_content=node.content,
        )
    except Exception as exc:
        node_logger.exception(
            "semantic_node_extraction_failed",
            duration_ms=round(
                (perf_counter() - extraction_started_at) * 1000,
                2,
            ),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    node_logger.info(
        "semantic_node_extraction_completed",
        duration_ms=round(
            (perf_counter() - extraction_started_at) * 1000,
            2,
        ),
        semantic_block_count=len(node.semantic_blocks),
    )
    node_logger.info(
        "semantic_node_processing_completed",
        duration_ms=round((perf_counter() - node_started_at) * 1000, 2),
    )


def _pre_semantic_noise_removal(
    root: MdNode,
    max_workers: int = 4,
) -> MdNode:
    """
    语义清洗前的预处理步骤
     1. 标准化content内容，调用_normalization_tree_content_llm方法
     2. 把语义提取出来，调用：_llm_extract_semantic方法

    不同节点之间没有数据依赖，使用有界线程池并发处理。
    """
    if max_workers < 1:
        raise ValueError("max_workers 必须大于等于 1")

    content_nodes: list[MdNode] = []
    stack: list[MdNode] = [root]
    while stack:
        node = stack.pop()
        if node.content:
            content_nodes.append(node)
        stack.extend(node.children)

    if not content_nodes:
        return root

    logger.info(
        "semantic_preprocessing_started",
        content_node_count=len(content_nodes),
        max_workers=min(max_workers, len(content_nodes)),
    )
    started_at = perf_counter()
    with ThreadPoolExecutor(
        max_workers=min(max_workers, len(content_nodes)),
        thread_name_prefix="prd-semantic",
    ) as executor:
        futures = [
            executor.submit(_normalize_and_extract_node, node)
            for node in content_nodes
        ]
        for future in futures:
            future.result()

    logger.info(
        "semantic_preprocessing_completed",
        content_node_count=len(content_nodes),
        duration_ms=round((perf_counter() - started_at) * 1000, 2),
    )
    return root


def semantic_noise_removal(
    root: MdNode,
    max_workers: int = 4,
) -> list[dict[str, Any]]:
    """
    语义噪声清洗
    :return:
    """
    result: list[dict[str, Any]] = []
    node = _pre_semantic_noise_removal(root, max_workers=max_workers)

    stack: list[MdNode] = [node]
    while len(stack) > 0:
        pop_node = stack.pop()
        removed_blocks = [
            x for x in pop_node.semantic_blocks if x.is_noise
        ]
        kept_blocks = [
            x for x in pop_node.semantic_blocks if not x.is_noise
        ]
        pop_node.semantic_blocks = kept_blocks
        result.append({
            "node_title": pop_node.title,
            "node_level": pop_node.level,
            "kept_blocks": kept_blocks,
            "removed_blocks": removed_blocks
        })
        stack.extend(reversed(pop_node.children))
    return result
