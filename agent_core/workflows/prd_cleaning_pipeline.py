from collections.abc import Callable
from time import perf_counter
from typing import Any, TypeVar

import structlog

from agent_core.common.test_utils import write_json_string_to_log
from agent_core.Infrastructure.prd.clean.enrichment_prd_md import enrichment_prd_md
from agent_core.Infrastructure.prd.clean.image_semantic_extraction import image_semantic_extraction
from agent_core.Infrastructure.prd.clean.semantic_noise_removal import semantic_noise_removal
from agent_core.Infrastructure.prd.clean.structural_cleaning import structural_cleaning
from agent_core.Infrastructure.prd.clean.structural_normalization import structural_normalization
from agent_core.Infrastructure.prd.standardization_prd_md import (
    standardization_prd_md_with_business_structure,
)
from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_pipeline_context import PrdPipelineContext


logger = structlog.get_logger(__name__)

T = TypeVar("T")


def _collect_tree_metrics(root: MdNode) -> dict[str, int]:
    """统计当前 PRD 树的关键规模指标。"""
    node_count = 0
    image_count = 0
    semantic_block_count = 0
    stack = [root]

    while stack:
        node = stack.pop()
        node_count += 1
        image_count += len(node.images)
        semantic_block_count += len(node.semantic_blocks)
        stack.extend(node.children)

    return {
        "node_count": node_count,
        "image_count": image_count,
        "semantic_block_count": semantic_block_count,
    }


def _write_md_node_snapshot(
    bound_logger: Any,
    stage: str,
    root: MdNode,
) -> None:
    """将指定阶段的完整 MdNode 树写入项目根目录的 log 文件夹。"""
    output_path = write_json_string_to_log(
        json_content=root.model_dump_json(),
        prefix=f"prd_cleaning_{stage}",
    )
    bound_logger.info(
        "pipeline_stage_snapshot_written",
        stage=stage,
        snapshot_path=str(output_path),
    )


def _run_stage(
    bound_logger: Any,
    stage: str,
    operation: Callable[[], T],
    metrics: Callable[[T], dict[str, Any]] | None = None,
) -> T:
    """执行单个 Pipeline 阶段并记录开始、完成、耗时和失败日志。"""
    started_at = perf_counter()
    bound_logger.info("pipeline_stage_started", stage=stage)

    try:
        result = operation()
    except Exception as exc:
        bound_logger.exception(
            "pipeline_stage_failed",
            stage=stage,
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise

    completion_fields: dict[str, Any] = {
        "stage": stage,
        "duration_ms": round((perf_counter() - started_at) * 1000, 2),
    }
    if metrics is not None:
        completion_fields.update(metrics(result))

    bound_logger.info("pipeline_stage_completed", **completion_fields)
    return result


class PrdCleaningPipeline:
    def run(self, input_path: str) -> PrdPipelineContext:
        pipeline_logger = logger.bind(input_path=input_path)
        pipeline_started_at = perf_counter()
        pipeline_logger.info("prd_cleaning_pipeline_started")

        try:
            root = _run_stage(
                pipeline_logger,
                "standardization",
                lambda: standardization_prd_md_with_business_structure(
                    input_path
                ),
                _collect_tree_metrics,
            )
            context = PrdPipelineContext(root=root)
            _write_md_node_snapshot(
                pipeline_logger,
                "standardization",
                root,
            )

            _run_stage(
                pipeline_logger,
                "structural_cleaning",
                lambda: structural_cleaning(root),
                lambda _: _collect_tree_metrics(root),
            )
            _write_md_node_snapshot(
                pipeline_logger,
                "structural_cleaning",
                root,
            )

            semantic_noise_removal_report = _run_stage(
                pipeline_logger,
                "semantic_noise_removal",
                lambda: semantic_noise_removal(root),
                lambda report: {
                    **_collect_tree_metrics(root),
                    "report_count": len(report),
                },
            )
            context.reports[
                "semantic_noise_removal"
            ] = semantic_noise_removal_report
            _write_md_node_snapshot(
                pipeline_logger,
                "semantic_noise_removal",
                root,
            )

            _run_stage(
                pipeline_logger,
                "image_semantic_extraction",
                lambda: image_semantic_extraction(root),
                lambda _: _collect_tree_metrics(root),
            )
            _write_md_node_snapshot(
                pipeline_logger,
                "image_semantic_extraction",
                root,
            )

            _run_stage(
                pipeline_logger,
                "structural_normalization",
                lambda: structural_normalization(root),
                lambda _: _collect_tree_metrics(root),
            )
            _write_md_node_snapshot(
                pipeline_logger,
                "structural_normalization",
                root,
            )

            _run_stage(
                pipeline_logger,
                "enrichment",
                lambda: enrichment_prd_md(root),
                lambda _: _collect_tree_metrics(root),
            )
            _write_md_node_snapshot(
                pipeline_logger,
                "enrichment",
                root,
            )
        except Exception as exc:
            pipeline_logger.exception(
                "prd_cleaning_pipeline_failed",
                duration_ms=round(
                    (perf_counter() - pipeline_started_at) * 1000,
                    2,
                ),
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise

        pipeline_logger.info(
            "prd_cleaning_pipeline_completed",
            duration_ms=round(
                (perf_counter() - pipeline_started_at) * 1000,
                2,
            ),
            report_names=list(context.reports),
            **_collect_tree_metrics(root),
        )
        return context


PrdCleaningPipeline().run(
    input_path="../test/test_prd.md"
)