import re
from itertools import count


from agent_core.common.file_utils import read_md_file
from agent_core.common.tree_utils import walk_md_tree
from agent_core.llm.base import call_mllm_with_image
from agent_core.models.prd.md_image_ref import MdImageRef
from agent_core.models.prd.md_node import MdNode
from agent_core.prompts.prd.parser_md_prompt import PARSER_MD_IMG_TO_NORMAL_TEXT_PROMPT


def _extract_md_title(md_title: str) -> tuple[str, int]:
    title = ""
    level = -1
    match = re.match(r"^(#{1,6})\s+(.*)$", md_title)
    if match:
        level = len(match.group(1))
        title = match.group(2)
    return title, level

def _parser_md_prd_to_tree(input_path: str) -> MdNode:
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




def _expand_md_node(node: MdNode) -> list[str]:
    """
    将md文档展开平铺为一个list
    """

def _prd_img_processor(root: MdNode) -> None:
    """
    处理prd中的图片
        1. 识别prd中的图片，提取出来，并在content中删除（避免后续影响normalization）
        2. 挂载node
    """
    MD_IMAGE_PATTERN = re.compile(
        r'!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)(?:\s+"(?P<title>[^"]*)")?\)'
    )
    def _walk(node: MdNode) -> None:
        images: list[MdImageRef] = []
        img_counter = count(1)
        for match in MD_IMAGE_PATTERN.finditer(node.content):
            alt = match.group("alt")
            src = match.group("src")
            title = match.group("title")
            raw = match.group(0)
            image = MdImageRef(
                id=f"img-{next(img_counter)}",raw_markdown=raw, src=src,alt_text=alt,title=title
            )
            images.append(image)

        node.images = images
        # 清空content的img标签
        node.content = MD_IMAGE_PATTERN.sub("", node.content)

    walk_md_tree(root, _walk)



def standardization_prd_md(input_path: str) -> MdNode:
    """
    标准化prd
    """
    node = _parser_md_prd_to_tree(input_path)
    _prd_img_processor(node)

    return node

# tree = _parser_md_prd_to_tree("/Users/weizhilong/Downloads/夜间签收管控.md")
# print(tree)