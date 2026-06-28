from typing import Any

from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_insert_vector_db_flow_result import PrdInsertVectorDBFlowResult


def _classify_node(mdNode: MdNode) -> tuple[list[MdNode], list[MdNode]]:
    """
    将mdNode分割成可入库和不可入库两类
    """
    insert_node = []
    exclude_node = []



    return insert_node, exclude_node


def prd_insert_vector_db_flow(mdNode: MdNode) -> PrdInsertVectorDBFlowResult:
    """
    prd插入向量库流程
    """
    result = PrdInsertVectorDBFlowResult()
    insert_node, exclude_node = _classify_node(mdNode)


    return result
