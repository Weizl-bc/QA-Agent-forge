import logging
from concurrent.futures import ThreadPoolExecutor

from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from agent_core.common.llm_result_validate_util import clean_llm_json_content
from agent_core.common.tree_utils import walk_md_tree
from agent_core.llm.base import create_model, call_mllm_with_image
from agent_core.models.prd.md_image_ref import MdImageRef
from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_semantic_block import PrdSemanticBlock
from agent_core.models.prd.prd_parser_img_model import (
    ImageAnalysisResult,
    ImageSemanticBlockResult,
)
from agent_core.prompts.prd.parser_md_prompt import (
    PARSER_MD_IMG_TO_NORMAL_TEXT_PROMPT,
    PARSER_IMG_TO_SEMANTIC_BLOCK_PROMPT,
)

logger = logging.getLogger(__name__)


def _parse_image_to_analysis(
    node: MdNode,
    image,
) -> ImageAnalysisResult:
    """
    使用第一个 Prompt：
    MdImageRef -> ImageAnalysisResult
    """

    image_prompt = PARSER_MD_IMG_TO_NORMAL_TEXT_PROMPT.format(
        source_title=image.source_title or node.title,
        source_node_path=image.source_node_path or node.title,
        alt_text=image.alt_text or "",
        before_text=node.normalized_content or node.content or "",
        after_text="",
    )

    raw_result = call_mllm_with_image(
        img_url=image.local_path or image.src,
        prompt=image_prompt,
    )

    content = clean_llm_json_content(raw_result)

    try:
        return ImageAnalysisResult.model_validate_json(content)
    except ValidationError:
        logger.warning("多模态模型返回无法解析为 ImageAnalysisResult, content=%s", content)
        raise


def _fill_image_ref_by_analysis(
    image,
    image_analysis: ImageAnalysisResult,
) -> None:
    """
    把图片结构化分析结果回填到 MdImageRef。
    """

    image.image_type = image_analysis.image_type
    image.is_noise = image_analysis.is_noise

    image.ocr_text = "\n".join(
        item.text
        for item in image_analysis.ocr_texts
        if item.text
    )

    image.visual_summary = image_analysis.business_summary


def _parse_image_analysis_to_semantic_blocks(
    llm,
    node: MdNode,
    image,
    image_analysis: ImageAnalysisResult,
) -> ImageSemanticBlockResult:
    """
    使用第二个 Prompt：
    ImageAnalysisResult -> ImageSemanticBlockResult
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", PARSER_IMG_TO_SEMANTIC_BLOCK_PROMPT),
    ])

    raw_result = (prompt | llm).invoke({
        "source_node_path": image.source_node_path or node.title,
        "source_title": image.source_title or node.title,
        "source_image_id": image.id,
        "image_analysis_json": image_analysis.model_dump_json(),
    })

    content = clean_llm_json_content(raw_result)

    try:
        return ImageSemanticBlockResult.model_validate_json(content)
    except ValidationError:
        logger.warning("图片语义块转换失败, content=%s", content)
        raise


def _process_image(
    node: MdNode,
    image: MdImageRef,
) -> list[PrdSemanticBlock]:
    """依次完成单张图片的多模态分析和语义块转换。"""
    image_analysis = _parse_image_to_analysis(node, image)
    _fill_image_ref_by_analysis(image, image_analysis)
    if image.is_noise:
        return []

    semantic_result = _parse_image_analysis_to_semantic_blocks(
        llm=create_model(0),
        node=node,
        image=image,
        image_analysis=image_analysis,
    )
    return semantic_result.semantic_blocks


def image_semantic_extraction(
    root: MdNode,
    max_workers: int = 3,
) -> None:
    """
    图片语义抽取。

    执行链路：
    MdImageRef
        -> 第一个 Prompt + 多模态模型
        -> ImageAnalysisResult
        -> 回填 MdImageRef
        -> 第二个 Prompt + 文本模型
        -> PrdSemanticBlock
        -> 追加到 node.semantic_blocks

    图片之间没有数据依赖，使用有界线程池并发处理；语义块由主线程回填。
    """
    if max_workers < 1:
        raise ValueError("max_workers 必须大于等于 1")

    image_tasks: list[tuple[MdNode, MdImageRef]] = []
    def handler(node: MdNode) -> None:
        for image in node.images:
            if not image.src and not image.local_path:
                logger.warning(
                    "图片地址为空, node_id=%s, image_id=%s",
                    node.id,
                    image.id,
                )
                continue
            image_tasks.append((node, image))

    walk_md_tree(root, handler)
    if not image_tasks:
        return

    with ThreadPoolExecutor(
        max_workers=min(max_workers, len(image_tasks)),
        thread_name_prefix="prd-image",
    ) as executor:
        futures = [
            (node, image, executor.submit(_process_image, node, image))
            for node, image in image_tasks
        ]
        for node, image, future in futures:
            try:
                node.semantic_blocks.extend(future.result())
            except Exception as exc:
                logger.exception(
                    "图片语义抽取失败, node_id=%s, image_id=%s, image_src=%s",
                    node.id,
                    image.id,
                    image.src,
                )

                if hasattr(image, "parse_error"):
                    image.parse_error = str(exc)
