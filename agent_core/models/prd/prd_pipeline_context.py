from dataclasses import field

from pydantic.dataclasses import dataclass

from agent_core.models.prd.md_node import MdNode


@dataclass
class PrdPipelineContext:
    root: MdNode
    reports: dict[str, object] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
