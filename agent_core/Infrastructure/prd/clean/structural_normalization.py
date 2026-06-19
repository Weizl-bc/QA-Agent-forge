import re

from agent_core.models.prd.md_node import MdNode

def _title_normalization(root: MdNode) -> MdNode:
    """
    标题标准化
        将标题中的空格、其他符号去除掉
    """
    stack = [root]
    while len(stack) > 0:
        node = stack.pop()

        title = node.title
        title = re.sub(r"^\d+(\.\d+)*\s*", "", title)  # 1.1 / 1.1.1
        title = re.sub(r"[（）()【】\[\]]", "", title)
        title = title.strip()

        node.title = title

        stack.extend(reversed(node.children))

def _structural_deduplication(root: MdNode) -> MdNode:
    """
    结构去重
        若多个节点表达的是一个意思，则合并
    """
    


def structural_normalization(root: MdNode) -> MdNode:
    """
    结构归一化
        1. 标题标准化 ：_title_normalization()

    :param root:
    :return:
    """
    _title_normalization(root)
    _structural_deduplication(root)
