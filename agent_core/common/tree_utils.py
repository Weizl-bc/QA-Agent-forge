from typing import Callable

from agent_core.models.prd.md_node import MdNode


def walk_md_tree(root: MdNode, handler: Callable[[MdNode], None]) -> None:
    """
    通用 MdNode 树遍历方法。
    使用栈进行深度优先遍历。
    handler 用于处理每一个节点。
    """
    stack = [root]
    while stack:
        node = stack.pop()
        handler(node)
        # reversed 是为了保持从左到右的遍历顺序
        stack.extend(reversed(node.children))

