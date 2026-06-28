from dataclasses import field

from pydantic import BaseModel

from agent_core.models.prd.md_node import MdNode


class PrdInsertVectorDBFlowResult(BaseModel):
    """

    """
    # 被排除的节点
    exclude_node: list[MdNode] = field(default_factory=list)
    # 插入的节点
    insert_nodes: list[MdNode] = field(default_factory=list)

