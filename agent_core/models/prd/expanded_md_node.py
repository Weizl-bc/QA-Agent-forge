from dataclasses import dataclass


@dataclass
class ExpandedMdNode:
    """
    将MdNode树形节点平铺后的节点。

    """

    level_str: str