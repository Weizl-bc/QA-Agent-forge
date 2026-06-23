from dataclasses import field
from typing import Callable

from pydantic import BaseModel, Field

from agent_core.models.prd.md_image_ref import MdImageRef
from agent_core.models.prd.page_ref import PageRef
from agent_core.models.prd.prd_semantic_block import PrdSemanticBlock


class MdNode(BaseModel):
    """
    md文件的树形结构
    例如：
     MdNode(level=1,title=PRD大纲,content="xxx")
        - MdNode(level=2,title=xxx)

    """

    id: str  # id用于在删除时区分具体节点
    title: str
    level: int
    content: str = ""
    source_path: str = ""
    normalized_content: str = ""    # LLM归一化结果
    is_retrievable: bool = True  # 是否允许进入业务知识向量库
    retrieval_reason: str = ""  # 可检索性判断依据
    node_type: str = "section"  # section / requirement / api / rule / reference（文件引用） / table（表格类型）
    semantic_blocks: list["PrdSemanticBlock"] = field(default_factory=list)
    children: list["MdNode"] = field(default_factory=list)  # 语义
    images: list[MdImageRef] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    page_refs: list[PageRef] = Field(default_factory=list)

    def remove_this_node(self, predicate: Callable[["MdNode"], bool]) -> int:
        """
        删除树中某一个节点
        :param predicate: 指定的某一个节点
        :return:            删除的数量
        """
        remove_count = 0
        new_children = []

        for child in self.children:
            if predicate(child):
                remove_count += 1
                continue

            remove_count += child.remove_this_node(predicate)
            new_children.append(child)

        self.children = new_children
        return remove_count
