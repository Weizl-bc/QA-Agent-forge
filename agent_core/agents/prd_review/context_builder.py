from dataclasses import dataclass, field

from agent_core.Infrastructure.prd.rag_pre_processor import rag_pre_processor
from agent_core.models.prd.md_node import MdNode


@dataclass(frozen=True)
class PrdReviewChunk:
    chunk_id: str
    content: str
    location_texts: dict[str, str]


@dataclass(frozen=True)
class PrdReviewDocumentContext:
    document_outline: str
    semantic_index: str
    chunks: list[PrdReviewChunk] = field(default_factory=list)


class PrdReviewContextBuilder:
    """把 MdNode 转换为 LLM 可消费且可回溯证据的评审上下文。"""

    def __init__(
        self,
        max_chunk_chars: int = 24_000,
        max_outline_chars: int = 8_000,
        max_semantic_index_chars: int = 12_000,
    ) -> None:
        if max_chunk_chars < 1:
            raise ValueError("max_chunk_chars 必须大于 0")
        self.max_chunk_chars = max_chunk_chars
        self.max_outline_chars = max_outline_chars
        self.max_semantic_index_chars = max_semantic_index_chars

    def build(self, root: MdNode) -> PrdReviewDocumentContext:
        entries = self._collect_entries(root)
        outline = "\n".join(
            f"- {location}" for location, _ in entries
        )[:self.max_outline_chars]
        semantic_index = self._build_semantic_index(root)
        chunks = self._build_chunks(entries)
        return PrdReviewDocumentContext(
            document_outline=outline,
            semantic_index=semantic_index,
            chunks=chunks,
        )

    def _collect_entries(
        self,
        root: MdNode,
    ) -> list[tuple[str, str]]:
        entries: list[tuple[str, str]] = []
        used_locations: set[str] = set()
        stack: list[tuple[MdNode, list[str]]] = [(root, [])]
        while stack:
            node, parent_titles = stack.pop()
            title = node.title.strip()
            current_titles = (
                parent_titles
                if node.id == "root"
                else [*parent_titles, title]
            )
            location = node.source_path or " / ".join(current_titles)
            if node.id != "root":
                if location in used_locations:
                    location = f"{location} [{node.id}]"
                used_locations.add(location)
                source_parts = [
                    title,
                    node.content.strip(),
                    *node.references,
                ]
                source_text = "\n".join(
                    dict.fromkeys(
                        part.strip()
                        for part in source_parts
                        if part and part.strip()
                    )
                )
                if source_text:
                    entries.append((location, source_text))
            for child in reversed(node.children):
                stack.append((child, current_titles))
        return entries

    def _build_semantic_index(self, root: MdNode) -> str:
        try:
            records = rag_pre_processor(root.model_copy(deep=True))
            texts = [record.text for record in records]
        except Exception:
            texts = []
        return "\n\n".join(texts)[:self.max_semantic_index_chars]

    def _build_chunks(
        self,
        entries: list[tuple[str, str]],
    ) -> list[PrdReviewChunk]:
        chunks: list[PrdReviewChunk] = []
        current_parts: list[str] = []
        current_locations: dict[str, str] = {}
        current_length = 0

        def flush() -> None:
            nonlocal current_parts, current_locations, current_length
            if not current_parts:
                return
            chunks.append(
                PrdReviewChunk(
                    chunk_id=f"chunk-{len(chunks) + 1}",
                    content="\n\n".join(current_parts),
                    location_texts=dict(current_locations),
                )
            )
            current_parts = []
            current_locations = {}
            current_length = 0

        for location, source_text in entries:
            entry = f"[节点路径] {location}\n[节点原文]\n{source_text}"
            if current_parts and current_length + len(entry) > self.max_chunk_chars:
                flush()
            if len(entry) <= self.max_chunk_chars:
                current_parts.append(entry)
                current_locations[location] = source_text
                current_length += len(entry)
                continue

            flush()
            prefix = f"[节点路径] {location}\n[节点原文]\n"
            available = max(1, self.max_chunk_chars - len(prefix))
            for start in range(0, len(source_text), available):
                part = source_text[start:start + available]
                chunks.append(
                    PrdReviewChunk(
                        chunk_id=f"chunk-{len(chunks) + 1}",
                        content=f"{prefix}{part}",
                        location_texts={location: part},
                    )
                )
        flush()
        return chunks
