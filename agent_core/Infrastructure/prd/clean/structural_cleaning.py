from agent_core.models.prd.md_node import MdNode

def structural_cleaning(root: MdNode):
    _clean_recursive(root)


def _clean_recursive(node: MdNode):
    # 先递归清理子树，再过滤当前层
    for child in node.children:
        _clean_recursive(child)
    node.children = [
        c for c in node.children
        if not (len(c.children) == 0 and len(c.content) == 0)
    ]