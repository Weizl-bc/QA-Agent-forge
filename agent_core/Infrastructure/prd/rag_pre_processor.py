import json
from pathlib import Path


from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_semantic_block import PrdSemanticBlock
from agent_core.models.prd.prd_vector_record import PrdVectorRecord


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENRICHMENT_SNAPSHOT_PATH = (
    PROJECT_ROOT
    / "log"
    / "prd_cleaning_enrichment_018bb837f2d949ffa69ed9f8cdd6e537.json"
)


def _build_search_text(
    node: MdNode,
    node_path: str,
    block: PrdSemanticBlock,
) -> str:
    """将节点上下文和语义块字段组合成用于 embedding 的文本。"""
    parts = [
        f"章节：{node_path}",
        f"节点类型：{node.node_type}",
        f"语义类型：{block.block_type}",
        f"内容：{block.raw_text.strip()}",
    ]
    optional_parts = (
        ("条件", block.conditions),
        ("动作", block.actions),
        ("约束", block.constraints),
        ("实体", block.entities),
    )
    for label, values in optional_parts:
        if values:
            parts.append(f"{label}：{'；'.join(values)}")
    return "\n".join(parts)


def _build_fallback_block(node: MdNode) -> PrdSemanticBlock | None:
    """当节点没有有效语义块时，使用清洗文本构造兜底语义块。"""
    content = (node.normalized_content or node.content).strip()
    if not content:
        return None
    return PrdSemanticBlock(
        raw_text=content,
        block_type=node.node_type or "section",
        source_type="content",
        source_node_path=node.source_path or None,
        source_title=node.title or None,
    )


def rag_pre_processor(
    node: MdNode,
    document_id: str | None = None,
) -> list[PrdVectorRecord]:
    """将 MdNode 树展平为可直接向量化的 PRD 记录。"""
    resolved_document_id = document_id or node.source_path or node.id
    records: list[PrdVectorRecord] = []

    def walk(current: MdNode, parent_titles: list[str]) -> None:
        current_titles = [
            *parent_titles,
            *([current.title.strip()] if current.title.strip() else []),
        ]
        node_path = " > ".join(current_titles)
        blocks: list[PrdSemanticBlock] = []
        if current.is_retrievable:
            blocks = [
                block
                for block in current.semantic_blocks
                if not block.is_noise and block.raw_text.strip()
            ]
            if not blocks:
                fallback_block = _build_fallback_block(current)
                blocks = (
                    [fallback_block]
                    if fallback_block is not None
                    else []
                )

        for block_index, block in enumerate(blocks):
            records.append(
                PrdVectorRecord(
                    id=(
                        f"{resolved_document_id}:"
                        f"{current.id}:block:{block_index}"
                    ),
                    text=_build_search_text(current, node_path, block),
                    document_id=resolved_document_id,
                    node_id=current.id,
                    node_path=node_path,
                    title=current.title,
                    node_level=current.level,
                    node_type=current.node_type,
                    source_path=current.source_path or node.source_path,
                    block_index=block_index,
                    block_type=block.block_type,
                    source_type=block.source_type,
                    conditions=block.conditions,
                    actions=block.actions,
                    constraints=block.constraints,
                    entities=block.entities,
                )
            )

        for child in current.children:
            walk(child, current_titles)

    walk(node, [])
    return records
