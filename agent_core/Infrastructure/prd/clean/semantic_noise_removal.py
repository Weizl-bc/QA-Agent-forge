import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from agent_core.common.llm_result_validate_util import validate_llm_result_of_str
from agent_core.llm.base import create_model
from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_semantic_block import PrdSemanticBlock
from agent_core.prompts.prd.parser_md_prompt import PARSER_MD_TO_NORMAL_TEXT_PROMPT
from agent_core.prompts.prd.senmatic_prompt import MD_NODE_TO_SEMANTIC_PROMPT


def _llm_extract_semantic(raw_content: str, normalized_content: str) -> list[PrdSemanticBlock]:
    """
    llm提取语义
    """

    llm = create_model(temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", MD_NODE_TO_SEMANTIC_PROMPT),
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
    raw_text = result.content

    data = json.loads(validate_llm_result_of_str(raw_text))

    blocks = [
        PrdSemanticBlock.model_validate(x)
        for x in data
    ]
    return blocks

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
    content = result.content
    return validate_llm_result_of_str(content)


def _pre_semantic_noise_removal(root: MdNode) -> MdNode:
    """
    语义清洗前的预处理步骤
     1. 标准化content内容，调用_normalization_tree_content_llm方法
     2. 把语义提取出来，调用：_llm_extract_semantic方法
    """
    stack: list[MdNode] = [root]
    while len(stack) > 0:
        node = stack.pop()
        if node.content:
            node.normalized_content = _normalization_tree_content_llm(node.content)
            node.semantic_blocks = _llm_extract_semantic(
                normalized_content=node.normalized_content,
                raw_content=node.content
            )

        for child in node.children:
            stack.append(child)

    return root

def semantic_noise_removal(root: MdNode) ->  list[dict[str, Any]]:
    """
    语义噪声清洗
    :return:
    """
    result: list[dict[str, Any]] = []
    node = _pre_semantic_noise_removal(root)

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
