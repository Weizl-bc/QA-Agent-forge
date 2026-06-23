from agent_core.models.prd.md_node import MdNode


def structural_cleaning(root: MdNode):
    _clean_recursive(root)


def _clean_recursive(node: MdNode):
    # 先递归清理子树，再过滤没有正文、引用或图片的空叶子节点。
    for child in node.children:
        _clean_recursive(child)
    node.children = [
        c for c in node.children
        if not (
            len(c.children) == 0
            and len(c.content) == 0
            and len(c.references) == 0
            and len(c.images) == 0
            and len(c.page_refs) == 0
        )
    ]
