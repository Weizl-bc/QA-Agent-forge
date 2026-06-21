import re
from dataclasses import dataclass, field
from itertools import count
from pathlib import Path
from typing import Iterator

from markdown_it import MarkdownIt
from markdown_it.token import Token

from agent_core.common.content_utils import remove_redundant_newlines
from agent_core.common.file_utils import read_md_file
from agent_core.common.tree_utils import walk_md_tree
from agent_core.llm.base import call_mllm_with_image
from agent_core.models.prd.md_image_ref import MdImageRef
from agent_core.models.prd.md_node import MdNode
from agent_core.prompts.prd.parser_md_prompt import PARSER_MD_IMG_TO_NORMAL_TEXT_PROMPT


# 旧解析流程和新 AST 解析流程共用同一套 Markdown 图片语法。
MD_IMAGE_PATTERN = re.compile(
    r'!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)'
    r'(?:\s+"(?P<title>[^"]*)")?\)'
)
MD_LINK_PATTERN = re.compile(
    r'\[(?P<label>[^\]]*)\]\((?P<target>[^)\s]+)'
    r'(?:\s+"[^"]*")?\)'
)
PLAIN_URL_PATTERN = re.compile(r"https?://[^\s<>()\[\]\"']+")
REFERENCE_FILE_PATTERN = re.compile(
    r"^(?:file://\S+|(?:[A-Za-z]:[\\/]|/|\./|\.\./)?\S+"
    r"\.(?:pdf|docx?|xlsx?|csv|pptx?|zip|rar))$",
    flags=re.IGNORECASE,
)

@dataclass
class MarkdownListItem:
    """
    Markdown 嵌套列表的中间模型。

    先把 markdown-it-py 的 token 流转换成简单列表树，再决定哪些列表项
    应提升为 MdNode。这样 Markdown 语法解析与 PRD 业务判断不会耦合。
    """

    text: str = ""
    children: list["MarkdownListItem"] = field(default_factory=list)
    images: list[MdImageRef] = field(default_factory=list)


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


def _prd_content_standardization(root: MdNode) -> None:
    def handler(node: MdNode) -> None:
        node.content = remove_redundant_newlines(node.content)
    walk_md_tree(root, handler)


def standardization_prd_md(input_path: str) -> MdNode:
    """
    标准化prd
    """
    node = _parser_md_prd_to_tree(input_path)
    _prd_img_processor(node)
    _prd_content_standardization(node)

    return node


# ============================================================================
# 新版 Markdown AST 结构化解析
# ============================================================================
# 以下实现是对旧流程的补充。原有 standardization_prd_md() 完整保留，
# 正式 Pipeline 使用新版入口；需要回退时仍可直接调用旧入口。


def _clean_inline_markdown(text: str) -> str:
    """
    清理标题或列表项中的展示型 Markdown 标记。

    只删除加粗、斜体、行内代码和链接外壳，不总结或改写业务文字。链接保留
    可读标签；标签为空时保留 URL，避免结构解析阶段丢失事实信息。
    """
    text = re.sub(
        r"\[([^\]]*)\]\(([^)]+)\)",
        lambda match: match.group(1).strip() or match.group(2).strip(),
        text,
    )
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"\1", text)
    return text.replace("`", "").strip()


def _normalize_reference(reference: str) -> str:
    """清理引用目标末尾可能被 URL 正则吞入的标点。"""
    return reference.rstrip(".,;:!?，。；：！？、")


def _split_text_and_references(text: str) -> tuple[str, list[str]]:
    """
    将列表项中的外部引用与业务正文分离。

    纯 URL、纯 Markdown 链接和纯附件名不会进入 content；带有业务说明的
    混合文本保留可读标签和说明，同时把链接目标写入 references。
    """
    references = [
        _normalize_reference(match.group("target"))
        for match in MD_LINK_PATTERN.finditer(text)
    ]
    text_without_links = MD_LINK_PATTERN.sub("", text)
    references.extend(
        _normalize_reference(match.group(0))
        for match in PLAIN_URL_PATTERN.finditer(text_without_links)
    )

    cleaned_text = _clean_inline_markdown(text)
    if not references and REFERENCE_FILE_PATTERN.fullmatch(cleaned_text):
        return "", [cleaned_text]
    if not references:
        return cleaned_text, []

    meaningful_remainder = _clean_inline_markdown(
        PLAIN_URL_PATTERN.sub("", text_without_links)
    ).strip(" \t\r\n，。；：;:、")
    if not meaningful_remainder:
        return "", list(dict.fromkeys(references))

    content_without_urls = PLAIN_URL_PATTERN.sub(
        "",
        MD_LINK_PATTERN.sub(
            lambda match: match.group("label"),
            text,
        ),
    )
    content = _clean_inline_markdown(content_without_urls).strip()
    return content, list(dict.fromkeys(references))


def _extract_images_from_text(
    text: str,
    image_counter: Iterator[int],
) -> tuple[str, list[MdImageRef]]:
    """
    从 Markdown 文本中提取图片，并返回去除图片语法后的文本。

    新解析器使用文档级图片计数器，确保 image id 全局唯一。图片的来源节点
    和路径会在整棵树完成后统一补充。
    """
    images: list[MdImageRef] = []
    for match in MD_IMAGE_PATTERN.finditer(text):
        images.append(
            MdImageRef(
                id=f"img-{next(image_counter)}",
                raw_markdown=match.group(0),
                src=match.group("src"),
                alt_text=match.group("alt"),
                title=match.group("title"),
            )
        )
    return MD_IMAGE_PATTERN.sub("", text).strip(), images


def _parse_markdown_list(
    tokens: list[Token],
    start_index: int,
    image_counter: Iterator[int],
) -> tuple[list[MarkdownListItem], int]:
    """
    递归解析 bullet_list/ordered_list token。

    返回列表项树和列表结束后的 token 下标。该步骤仅还原 Markdown 层级，
    不判断列表项是否属于业务模块。
    """
    close_type = tokens[start_index].type.replace("_open", "_close")
    items: list[MarkdownListItem] = []
    index = start_index + 1

    while index < len(tokens) and tokens[index].type != close_type:
        if tokens[index].type == "list_item_open":
            item, index = _parse_markdown_list_item(
                tokens,
                index,
                image_counter,
            )
            items.append(item)
        else:
            index += 1

    return items, index + 1


def _parse_markdown_list_item(
    tokens: list[Token],
    start_index: int,
    image_counter: Iterator[int],
) -> tuple[MarkdownListItem, int]:
    """
    解析单个 list_item。

    一个列表项可以同时包含正文、图片、代码块和多个子列表。正文按原顺序
    合并；子列表递归写入 children。
    """
    text_parts: list[str] = []
    images: list[MdImageRef] = []
    child_items: list[MarkdownListItem] = []
    index = start_index + 1

    while index < len(tokens) and tokens[index].type != "list_item_close":
        token = tokens[index]

        if token.type == "inline":
            clean_text, inline_images = _extract_images_from_text(
                token.content,
                image_counter,
            )
            if clean_text:
                text_parts.append(clean_text)
            images.extend(inline_images)
            index += 1
            continue

        if token.type in {"bullet_list_open", "ordered_list_open"}:
            children, index = _parse_markdown_list(
                tokens,
                index,
                image_counter,
            )
            child_items.extend(children)
            continue

        if token.type in {"fence", "code_block"} and token.content.strip():
            text_parts.append(token.content.strip())

        index += 1

    return (
        MarkdownListItem(
            text="\n".join(text_parts).strip(),
            children=child_items,
            images=images,
        ),
        index + 1,
    )


def _extract_list_item_title_and_content(text: str) -> tuple[str, str]:
    """
    从列表项中分离业务标题和同行说明。

    示例：
      ``**批量导入：**使用菜鸟模板`` -> ("批量导入", "使用菜鸟模板")
      ``发货逻辑：``                  -> ("发货逻辑", "")

    加粗标题后的括号说明会保留在 content 中，供后续语义噪声清洗判断。
    """
    bold_match = re.match(r"^\s*\*\*(.+?)\*\*(.*)$", text, flags=re.S)
    if bold_match:
        title = _clean_inline_markdown(bold_match.group(1)).rstrip("：:")
        remaining = bold_match.group(2).strip()
        return title, remaining

    clean_text = _clean_inline_markdown(text)
    return clean_text.rstrip("：:"), ""


def _should_promote_list_item(item: MarkdownListItem) -> bool:
    """
    仅根据 Markdown 树结构判断列表项是否应提升为 MdNode。

    这里故意不使用任何业务关键词、标题枚举或领域词典，否则解析器只能适配
    某一类 PRD。通用规则只有两条：

      1. 当前列表项必须包含可读文本；
      2. 当前列表项必须拥有子列表。

    因此，所有“父列表项”都会成为结构节点，所有没有子列表的“叶子列表项”
    都会作为事实、字段或枚举值留在最近父节点的 content 中。结构判断完全
    由 Markdown 作者已经表达出的层级关系决定，不推测具体业务语义。
    """
    if not item.children:
        return False

    title, _ = _extract_list_item_title_and_content(item.text)
    return bool(title)


def _append_node_content(node: MdNode, text: str) -> None:
    """
    将字段、枚举或说明追加到当前业务节点 content。

    一行保留一个事实单元。结构阶段不做语义归并，后续现有 LLM 标准化步骤
    仍可将同类字段整理成一句话。
    """
    clean_text = _clean_inline_markdown(text)
    if not clean_text:
        return
    node.content = (
        f"{node.content}\n{clean_text}"
        if node.content
        else clean_text
    )


def _convert_list_items_to_md_nodes(
    items: list[MarkdownListItem],
    parent: MdNode,
    node_counter: Iterator[int],
) -> None:
    """
    将中间列表树转换为 MdNode 子树。

    - 拥有子列表的父列表项创建新 MdNode；
    - 字段、枚举和普通说明写入最近业务节点的 content；
    - 图片挂到当前最深业务节点；
    - 无文本父项不会建空节点，其后代仍按相同结构规则继续处理。
    """
    for item in items:
        if _should_promote_list_item(item):
            title, remaining_content = _extract_list_item_title_and_content(
                item.text
            )
            content, references = _split_text_and_references(
                remaining_content
            )
            business_node = MdNode(
                id=f"node-{next(node_counter)}",
                title=title,
                level=parent.level + 1,
                content=content,
                images=list(item.images),
                references=references,
            )
            parent.children.append(business_node)
            _convert_list_items_to_md_nodes(
                item.children,
                business_node,
                node_counter,
            )
            continue

        content, references = _split_text_and_references(item.text)
        if content:
            _append_node_content(parent, content)
        parent.references.extend(
            reference
            for reference in references
            if reference not in parent.references
        )
        parent.images.extend(item.images)
        _convert_list_items_to_md_nodes(
            item.children,
            parent,
            node_counter,
        )


def _split_oversized_text(content: str, max_chars: int) -> list[str]:
    """
    将超长正文拆成不超过 max_chars 的片段。

    优先使用现有换行；单行过长时按中英文句末符号拆分；最后才固定字符
    切片。该函数不总结、不改写任何业务文字。
    """
    if len(content) <= max_chars:
        return [content]

    logical_lines: list[str] = []
    for line in content.splitlines():
        stripped_line = line.strip()
        if not stripped_line:
            continue
        if len(stripped_line) <= max_chars:
            logical_lines.append(stripped_line)
            continue

        sentences = [
            sentence.strip()
            for sentence in re.split(
                r"(?<=[。！？；.!?;])",
                stripped_line,
            )
            if sentence.strip()
        ]
        for sentence in sentences:
            if len(sentence) <= max_chars:
                logical_lines.append(sentence)
            else:
                logical_lines.extend(
                    sentence[start:start + max_chars]
                    for start in range(0, len(sentence), max_chars)
                )

    chunks: list[str] = []
    current_lines: list[str] = []
    current_length = 0
    for line in logical_lines:
        separator_length = 1 if current_lines else 0
        if (
            current_lines
            and current_length + separator_length + len(line) > max_chars
        ):
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_length = 0
            separator_length = 0

        current_lines.append(line)
        current_length += separator_length + len(line)

    if current_lines:
        chunks.append("\n".join(current_lines))
    return chunks


def _split_oversized_node_content(
    root: MdNode,
    node_counter: Iterator[int],
    max_chars: int,
) -> None:
    """
    对业务拆分后仍超长的节点执行最后兜底拆分。

    原节点保留标题和业务子节点；正文移动到“内容分段N”子节点，并放在原有
    子节点之前，以维持正文先于子模块的阅读顺序。
    """
    stack = [root]
    while stack:
        node = stack.pop()
        original_children = list(node.children)

        if len(node.content) > max_chars:
            chunks = _split_oversized_text(node.content, max_chars)
            segment_nodes = [
                MdNode(
                    id=f"node-{next(node_counter)}",
                    title=f"{node.title}-内容分段{index}",
                    level=node.level + 1,
                    content=chunk,
                )
                for index, chunk in enumerate(chunks, start=1)
            ]
            node.content = ""
            node.children = segment_nodes + original_children

        stack.extend(reversed(node.children))


def _fill_image_source_context(root: MdNode) -> None:
    """为图片补充所属节点 id、标题和完整业务路径。"""
    stack: list[tuple[MdNode, list[str]]] = [(root, [])]
    while stack:
        node, parent_path = stack.pop()
        current_path = (
            parent_path
            if node.id == "root"
            else [*parent_path, node.title]
        )
        path_text = " / ".join(current_path)

        for image in node.images:
            image.source_node_id = node.id
            image.source_title = node.title
            image.source_node_path = path_text

        for child in reversed(node.children):
            stack.append((child, current_path))


def _parser_md_prd_to_business_tree(
    input_path: str,
    max_node_content_chars: int = 2000,
) -> MdNode:
    """
    使用 markdown-it-py 构造细粒度 PRD 业务树。

    规则：
      1. Markdown 标题始终创建 MdNode；
      2. 所有拥有子列表的父列表项提升为 MdNode；
      3. 字段、枚举和普通说明保留在最近业务节点的 content；
      4. 图片挂到其所在的最近业务节点；
      5. content 超过阈值时进行确定性兜底拆分。
    """
    if max_node_content_chars < 1:
        raise ValueError("max_node_content_chars 必须大于等于 1")

    markdown_text = Path(input_path).read_text(encoding="utf-8")
    tokens = MarkdownIt("commonmark").parse(markdown_text)
    root = MdNode(id="root", title="ROOT", level=0)
    node_counter = count(1)
    image_counter = count(1)
    heading_stack: list[MdNode] = [root]
    current_node = root
    index = 0

    while index < len(tokens):
        token = tokens[index]

        if token.type == "heading_open":
            heading_level = int(token.tag[1:])
            heading_text = (
                tokens[index + 1].content
                if index + 1 < len(tokens)
                else ""
            )
            title = _clean_inline_markdown(heading_text)

            while (
                len(heading_stack) > 1
                and heading_stack[-1].level >= heading_level
            ):
                heading_stack.pop()

            parent = heading_stack[-1]
            current_node = MdNode(
                id=f"node-{next(node_counter)}",
                title=title,
                level=heading_level,
            )
            parent.children.append(current_node)
            heading_stack.append(current_node)
            index += 3
            continue

        if token.type in {"bullet_list_open", "ordered_list_open"}:
            items, index = _parse_markdown_list(
                tokens,
                index,
                image_counter,
            )
            _convert_list_items_to_md_nodes(
                items,
                current_node,
                node_counter,
            )
            continue

        if token.type == "inline":
            clean_text, images = _extract_images_from_text(
                token.content,
                image_counter,
            )
            content, references = _split_text_and_references(clean_text)
            if content:
                _append_node_content(current_node, content)
            current_node.references.extend(
                reference
                for reference in references
                if reference not in current_node.references
            )
            current_node.images.extend(images)
            index += 1
            continue

        if token.type in {"fence", "code_block"}:
            _append_node_content(current_node, token.content)

        index += 1

    _prd_content_standardization(root)
    _split_oversized_node_content(
        root,
        node_counter,
        max_node_content_chars,
    )
    _fill_image_source_context(root)
    return root


def standardization_prd_md_with_business_structure(
    input_path: str,
    max_node_content_chars: int = 2000,
) -> MdNode:
    """
    新版标准化入口：解析 Markdown 标题、嵌套列表和图片业务归属。

    正式 Pipeline 已使用该入口；原有 standardization_prd_md() 完整保留，
    供旧行为兼容、结果对比或紧急回退。
    """
    return _parser_md_prd_to_business_tree(
        input_path=input_path,
        max_node_content_chars=max_node_content_chars,
    )


# tree = _parser_md_prd_to_tree("/Users/weizhilong/Downloads/夜间签收管控.md")
# print(tree)
