import structlog
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from agent_core.common.env_config import get_env, get_required_env
from agent_core.prompts.prd.parser_md_prompt import PARSER_MD_IMG_TO_NORMAL_TEXT_PROMPT

logger = structlog.get_logger(__name__)

def create_model(
    temperature: float = 0.1,
    max_retries: int | None = None,
) -> BaseChatModel:
    model_name = get_required_env("LLM_CHAT_MODEL_NAME")
    base_url = get_required_env("LLM_BASE_URL")
    api_key = get_required_env("LLM_API_KEY")
    request_timeout = float(get_env("LLM_REQUEST_TIMEOUT", "180"))
    resolved_max_retries = (
        int(get_env("LLM_MAX_RETRIES", "2"))
        if max_retries is None
        else max_retries
    )

    if not model_name:
        raise ValueError("缺少环境变量：LLM_CHAT_MODEL_NAME")

    if not base_url:
        raise ValueError("缺少环境变量：LLM_BASE_URL")

    if not api_key:
        raise ValueError("缺少环境变量：LLM_API_KEY")

    return init_chat_model(
        model=model_name,
        model_provider="openai",
        base_url=base_url,
        temperature=temperature,
        api_key=api_key,
        timeout=request_timeout,
        max_retries=resolved_max_retries,
    )


def create_mllm(temperature: float = 0.1) -> BaseChatModel:
    model_name = get_required_env("MLLM_MODEL_NAME")
    base_url = get_required_env("MLLM_BASE_URL")
    api_key = get_required_env("MLLM_API_KEY")
    request_timeout = float(get_env("MLLM_REQUEST_TIMEOUT", "180"))
    max_retries = int(get_env("MLLM_MAX_RETRIES", "2"))

    if not model_name:
        raise ValueError("缺少环境变量：MLLM_MODEL_NAME")

    if not base_url:
        raise ValueError("缺少环境变量：MLLM_BASE_URL")

    if not api_key:
        raise ValueError("缺少环境变量：MLLM_API_KEY")

    return init_chat_model(
        model=model_name,
        model_provider="openai",
        base_url=base_url,
        temperature=temperature,
        api_key=api_key,
        timeout=request_timeout,
        max_retries=max_retries,
    )


def call_mllm_with_image(img_url: str, prompt: str, temperature: float = 0.1) -> str:
    model = create_mllm(temperature=temperature)
    message = {
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": img_url}},
        ],
    }
    result = model.invoke([message])
    return result.content


if __name__ == "__main__":
    logger.info("开始调用模型")
    print(create_model().invoke("你是什么模型"))
    logger.info("模型调用结束")
