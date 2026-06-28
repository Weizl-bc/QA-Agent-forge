from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_semantic_block import PrdSemanticBlock

def is_business_node(node: MdNode | PrdSemanticBlock) -> bool:
    """
    判断节点是否是业务节点
    """
    
    if isinstance(node, MdNode):
        return node.is_retrievable

    if isinstance(node, PrdSemanticBlock):
        return not node.is_noise

    raise TypeError(f"不支持的节点类型：{type(node)}")