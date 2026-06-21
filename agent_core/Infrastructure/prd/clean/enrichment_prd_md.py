from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from langchain_core.prompts import ChatPromptTemplate

from agent_core.common.llm_result_validate_util import parse_llm_string_list
from agent_core.common.tree_utils import walk_md_tree
from agent_core.llm.base import create_model
from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_semantic_block import PrdSemanticBlock
from agent_core.prompts.prd.enrichment_prd_prompt import (
    ENRICHMENT_SEMANTIC_ACTIONS_PROMPT,
    ENRICHMENT_SEMANTIC_BLOCK_USER_PROMPT,
    ENRICHMENT_SEMANTIC_CONDITIONS_PROMPT,
    ENRICHMENT_SEMANTIC_CONSTRAINTS_PROMPT,
    ENRICHMENT_SEMANTIC_ENTITIES_PROMPT,
)


def _enrichment_semantic_entities(block: PrdSemanticBlock) -> None:
    """
    语义增强：实体
    """
    llm = create_model(temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", ENRICHMENT_SEMANTIC_ENTITIES_PROMPT),
        ("user", ENRICHMENT_SEMANTIC_BLOCK_USER_PROMPT),
    ])
    chain = prompt | llm
    result = chain.invoke({"raw_text": block.raw_text})
    block.entities = parse_llm_string_list(result, "entities")


def _enrichment_semantic_constraints(block: PrdSemanticBlock) -> None:
    """
    语义增强：约束
    """
    llm = create_model(temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", ENRICHMENT_SEMANTIC_CONSTRAINTS_PROMPT),
        ("user", ENRICHMENT_SEMANTIC_BLOCK_USER_PROMPT),
    ])
    chain = prompt | llm
    result = chain.invoke({"raw_text": block.raw_text})
    block.constraints = parse_llm_string_list(result, "constraints")


def _enrichment_semantic_actions(block: PrdSemanticBlock) -> None:
    """
    语义增强：动作
    """
    llm = create_model(temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", ENRICHMENT_SEMANTIC_ACTIONS_PROMPT),
        ("user", ENRICHMENT_SEMANTIC_BLOCK_USER_PROMPT),
    ])
    chain = prompt | llm
    result = chain.invoke({"raw_text": block.raw_text})
    block.actions = parse_llm_string_list(result, "actions")


def _enrichment_semantic_conditions(block: PrdSemanticBlock) -> None:
    """
    语义增强：条件
    """
    llm = create_model(temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", ENRICHMENT_SEMANTIC_CONDITIONS_PROMPT),
        ("user", ENRICHMENT_SEMANTIC_BLOCK_USER_PROMPT),
    ])
    chain = prompt | llm
    result = chain.invoke({"raw_text": block.raw_text})
    block.conditions = parse_llm_string_list(result, "conditions")


def _enrichment_semantic_block(block: PrdSemanticBlock) -> None:
    """
    语义增强四种业务规则
    1. 条件
    2. 动作
    3. 约束
    4. 实体
    """
    _enrichment_semantic_actions(block)
    _enrichment_semantic_conditions(block)
    _enrichment_semantic_constraints(block)
    _enrichment_semantic_entities(block)


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
    max_workers: int = 4,
) -> None:
    """
    语义增强。

    每个语义块的动作、条件、约束、实体提取都是独立任务。
    所有任务共用一个有界线程池，避免嵌套线程导致请求数失控。
    """
    if max_workers < 1:
        raise ValueError("max_workers 必须大于等于 1")

    tasks: list[
        tuple[Callable[[PrdSemanticBlock], None], PrdSemanticBlock]
    ] = []
    def handler(node: MdNode) -> None:
        _enrichment_md_node_type(node)
        for block in node.semantic_blocks:
            tasks.extend([
                (_enrichment_semantic_actions, block),
                (_enrichment_semantic_conditions, block),
                (_enrichment_semantic_constraints, block),
                (_enrichment_semantic_entities, block),
            ])

    walk_md_tree(mdNode, handler)

    if not tasks:
        return

    with ThreadPoolExecutor(
        max_workers=min(max_workers, len(tasks)),
        thread_name_prefix="prd-enrichment",
    ) as executor:
        futures = [
            executor.submit(task, block)
            for task, block in tasks
        ]
        for future in futures:
            future.result()
