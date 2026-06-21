import json
import re
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import Any

import structlog
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from agent_core.common.content_utils import remove_redundant_newlines
from agent_core.common.llm_result_validate_util import (
    clean_llm_json_content,
    extract_llm_content,
)
from agent_core.llm.base import create_model
from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_semantic_block import PrdSemanticBlock
from agent_core.prompts.prd.parser_md_prompt import PARSER_MD_TO_NORMAL_TEXT_PROMPT
from agent_core.prompts.prd.senmatic_prompt import (
    MD_NODE_TO_SEMANTIC_PROMPT,
    NORMALIZED_CONTENT_SEMANTIC_REPAIR_PROMPT,
    NORMALIZED_CONTENT_SEMANTIC_USER_PROMPT,
    NORMALIZED_CONTENT_TO_SEMANTIC_PROMPT,
)


logger = structlog.get_logger(__name__)

MAX_SEMANTIC_PARSE_ATTEMPTS = 2
URL_ONLY_PATTERN = re.compile(r"^https?://\S+$")


def _extract_url_only_references(content: str) -> list[str]:
    """仅当正文由一个或多个 URL 行组成时返回这些引用。"""
    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip()
    ]
    if lines and all(URL_ONLY_PATTERN.fullmatch(line) for line in lines):
        return list(dict.fromkeys(lines))
    return []


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


def _llm_extract_semantic(normalized_content: str) -> list[PrdSemanticBlock]:
    """
    仅根据标准化文本提取语义块。

    标准化文本是唯一事实来源。模型返回格式错误时，携带错误信息和原始
    输出进行一次纠错重试。
    """
    if not normalized_content or not normalized_content.strip():
        return []

    llm = create_model(temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=NORMALIZED_CONTENT_TO_SEMANTIC_PROMPT),
        ("user", NORMALIZED_CONTENT_SEMANTIC_USER_PROMPT),
    ])
    result = (prompt | llm).invoke({
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
                SystemMessage(content=NORMALIZED_CONTENT_TO_SEMANTIC_PROMPT),
                ("user", NORMALIZED_CONTENT_SEMANTIC_REPAIR_PROMPT),
            ])
            result = (repair_prompt | llm).invoke({
                "error": str(exc),
                "invalid_output": response_content,
                "normalized_content": normalized_content,
            })

    raise RuntimeError("语义提取重试流程异常结束")


def _llm_extract_semantic_with_raw_content(
    raw_content: str,
    normalized_content: str,
) -> list[PrdSemanticBlock]:
    """
    llm提取语义（和原文比较 费token）
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
3. 标准化文本遗漏的信息仍需从原始文本中提取。
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
                method="_llm_extract_semantic_with_raw_content",
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

    url_references = _extract_url_only_references(node.content)
    if url_references:
        node.references.extend(
            reference
            for reference in url_references
            if reference not in node.references
        )
        node.content = ""
        node.normalized_content = ""
        node.semantic_blocks = []
        node_logger.info(
            "semantic_node_normalization_skipped",
            reason="url_only_content",
            reference_count=len(url_references),
        )
        return

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
     2. 仅根据 normalized_content 调用 _llm_extract_semantic 提取语义

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


if __name__ == "__main__": print(_llm_extract_semantic_with_raw_content(normalized_content="""
打单发货-订单管理页面
1. 待发货Tab
表格查询条件筛选：创建时间、收件人姓名、收件人手机、收件省市。
表格字段：订单号、物流产品、收件人名称、发件人名称、发件人手机号、发件城市、包裹重量（只有两种：寄付、到付）、物品类型、保价（只有两种：是、否）、货品声明价值、备注、揽收时间（默认为当日揽）、创建时间。
在表格上方包含功能按钮：批量导入、批量发货。
""",
raw_content=remove_redundant_newlines("""
#### PC端整体页面结构：

*   **打单发货：**
    
    *   **订单管理**
        
        *   **发货打单**
            
            *   **待发货**
                
                *   **查询条件筛选项：**筛选条件无创建时间时，默认查询最近三个月的数据
                    
                    *   创建时间
                        
                    *   收件人姓名
                        
                    *   收件人手机
                        
                    *   收件省市
                        
                *   **明细字段：**
                    
                    *   订单号
                        
                    *   物流产品：
                        
                        *   本期默认为「菜鸟标快」
                            
                    *   收件人名称
                        
                    *   收件人手机号
                        
                    *   收件人地址
                        
                    *   发件人名称
                        
                    *   发件人手机号
                        
                    *   发件城市
                        
                    *   包裹重量
                        
                    *   支付方式：
                        
                        *   寄付
                            
                        *   到付
                            
                    *   物品类型
                        
                    *   保价：
                        
                        *   是
                            
                        *   否
                            
                    *   货品声明价值
                        
                    *    备注
                        
                    *   揽收时间：
                        
                        *   默认为「当日揽」
                            
                    *   创建时间
                        
                *   **批量导入：**使用菜鸟模版[菜鸟速递订单导入模板（最多一次导入1000条）.xlsx](https://view.officeapps.live.com/op/view.aspx?src=https%3A%2F%2Fcilogistics-oss.oss-cn-hangzhou.aliyuncs.com%2Fcnd%2F%25E8%258F%259C%25E9%25B8%259F%25E9%2580%259F%25E9%2580%2592%25E8%25AE%25A2%25E5%258D%2595%25E5%25AF%25BC%25E5%2585%25A5%25E6%25A8%25A1%25E6%259D%25BF%25EF%25BC%2588%25E6%259C%2580%25E5%25A4%259A%25E4%25B8%2580%25E6%25AC%25A1%25E5%25AF%25BC%25E5%2585%25A51000%25E6%259D%25A1%25EF%25BC%2589.xlsx&wdOrigin=BROWSELINK)
                    
                    *   导单过程中有进度提醒
                        
                    *   导单完成后，如有导入失败的情况，页面空白处会显示导入错误的行，与错误原因
                        
                    *   导入的订单可以在”导入记录“查看
                        
                    *   单次导入上限：1000条，
                        
                *   **批量发货：****（批量发货的上限？）**
                    
                    *   发货逻辑：
                        
                        *   默认揽收时间为「当日揽」，即90服务产品
                            
                        *   默认物流产品为「菜鸟标快」
                            
                        *   不支持包装服务，若客户有包装诉求，可在小件员端让小件员进行添加
                 
""")))
