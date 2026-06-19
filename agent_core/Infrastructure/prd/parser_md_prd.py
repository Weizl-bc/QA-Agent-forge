import re
from itertools import count


from agent_core.common.file_utils import read_md_file
from agent_core.models.prd.md_node import MdNode


def _extract_md_title(md_title: str) -> tuple[str, int]:
    title = ""
    level = -1
    match = re.match(r"^(#{1,6})\s+(.*)$", md_title)
    if match:
        level = len(match.group(1))
        title = match.group(2)
    return title, level

def parser_md_prd_to_tree(input_path: str) -> MdNode:
    """
    Markdown -> MdNode Tree
    返回 ROOT 节点
    """

    lines = read_md_file(input_path)
    root = MdNode(id="root",title="ROOT",level=0)

    id_counter = count(1)
    stack: list[MdNode] = [root]
    current_node: MdNode | None = None

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line:
            continue

        # 标题
        if line.startswith("#"):
            title, level = _extract_md_title(line)

            if level == -1:
                continue

            node = MdNode(id=f"node-{next(id_counter)}",
                          title=title,
                          level=level)
            # 找父节点
            while stack and stack[-1].level >= level:
                stack.pop()

            parent = stack[-1]
            parent.children.append(node)
            stack.append(node)
            current_node = node

        # 正文
        else:
            if current_node is None:
                continue
            if current_node.content:
                current_node.content += "\n"
            current_node.content += line
    return root


def expand_md_node(node: MdNode) -> list[str]:
    """
    将md文档展开平铺为一个list
    :param node:
    :return:
    """


# tree = _parser_md_prd_to_tree("/Users/weizhilong/Downloads/夜间签收管控.md")
# print(tree)