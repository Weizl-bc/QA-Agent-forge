import logging

from langchain_core.prompts import ChatPromptTemplate
from pydantic import ValidationError

from agent_core.common.llm_result_validate_util import clean_llm_json_content
from agent_core.common.tree_utils import walk_md_tree
from agent_core.llm.base import create_model, call_mllm_with_image
from agent_core.models.prd.md_node import MdNode
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


def image_semantic_extraction(root: MdNode) -> None:
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
    """

    llm = create_model(0)

    def handler(node: MdNode) -> None:
        for image in node.images:
            if not image.src and not image.local_path:
                logger.warning(
                    "图片地址为空, node_id=%s, image_id=%s",
                    node.id,
                    image.id,
                )
                continue

            try:
                image_analysis = _parse_image_to_analysis(node, image)
                _fill_image_ref_by_analysis(image, image_analysis)
                if image.is_noise:
                    continue

                semantic_result = _parse_image_analysis_to_semantic_blocks(
                    llm=llm,
                    node=node,
                    image=image,
                    image_analysis=image_analysis,
                )

                node.semantic_blocks.extend(semantic_result.semantic_blocks)

            except Exception as e:
                logger.exception(
                    "图片语义抽取失败, node_id=%s, image_id=%s, image_src=%s",
                    node.id,
                    image.id,
                    image.src,
                )

                if hasattr(image, "parse_error"):
                    image.parse_error = str(e)

    walk_md_tree(root, handler)
