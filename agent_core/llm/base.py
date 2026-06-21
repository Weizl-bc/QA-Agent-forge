from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from agent_core.common.env_config import get_required_env
from agent_core.prompts.prd.parser_md_prompt import PARSER_MD_IMG_TO_NORMAL_TEXT_PROMPT


def create_model(temperature: float = 0.1,) -> BaseChatModel:
    model_name = get_required_env("LLM_CHAT_MODEL_NAME")
    base_url = get_required_env("LLM_BASE_URL")
    api_key = get_required_env("LLM_API_KEY")

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
    )


def create_mllm(temperature: float = 0.1) -> BaseChatModel:
    model_name = get_required_env("MLLM_MODEL_NAME")
    base_url = get_required_env("MLLM_BASE_URL")
    api_key = get_required_env("MLLM_API_KEY")

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
    print(call_mllm_with_image(
        "https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/a/6KYkegJwXTGAPzEb/38d948d4f0c64ca092378470dc76eafa3905.png",
        PARSER_MD_IMG_TO_NORMAL_TEXT_PROMPT,
    ))
