from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from agent_core.common.env_config import get_required_env



def create_model(
        temperature: float = 0.1,
) -> BaseChatModel:
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
