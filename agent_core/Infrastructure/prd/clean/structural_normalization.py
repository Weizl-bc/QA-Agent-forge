import re

from agent_core.common.tree_utils import walk_md_tree
from agent_core.models.prd.md_node import MdNode

def _title_normalization(root: MdNode) -> None:
    """
    标题标准化
        将标题中的空格、其他符号去除掉
    """

    def _walk(node: MdNode) -> None:
        """
        清洗 MdNode 标题。
        """
        title = node.title
        title = re.sub(r"^\d+(\.\d+)*\s*", "", title)
        title = re.sub(r"[（）()【】\[\]]", "", title)
        title = title.strip()
        node.title = title

    walk_md_tree(root, _walk)

def _structural_deduplication(root: MdNode) -> MdNode:
    """
    结构去重
        若多个节点表达的是一个意思，则合并
    """

    # todo



def structural_normalization(root: MdNode) -> MdNode:
    """
    结构归一化
        1. 标题标准化 ：_title_normalization()

    :param root:
    :return:
    """
    _title_normalization(root)
    _structural_deduplication(root)
