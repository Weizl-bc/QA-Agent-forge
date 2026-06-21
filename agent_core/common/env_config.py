import os
from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=False)

def get_required_env(key: str) -> str:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        raise ValueError(f"缺少环境变量：{key}")
    return value


def get_env(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    return value


@dataclass(frozen=True)
class Settings:
    # LLM Chat
    llm_chat_model_name: str
    llm_base_url: str
    llm_api_key: str

    # LLM Text Embedding
    llm_text_embedding_base_url: str
    llm_text_embedding_api_key: str
    llm_text_embedding_model_name: str

    # MLLM (多模态)
    mllm_base_url: str
    mllm_api_key: str
    mllm_model_name: str


settings = Settings(
    # LLM Chat
    llm_chat_model_name=get_required_env("LLM_CHAT_MODEL_NAME"),
    llm_base_url=get_required_env("LLM_BASE_URL"),
    llm_api_key=get_required_env("LLM_API_KEY"),
    # LLM Text Embedding
    llm_text_embedding_base_url=get_required_env("LLM_TEXT_EMBEDDING_BASE_URL"),
    llm_text_embedding_api_key=get_required_env("LLM_TEXT_EMBEDDING_API_KEY"),
    llm_text_embedding_model_name=get_required_env("LLM_TEXT_EMBEDDING_MODEL_NAME"),
    # MLLM
    mllm_base_url=get_required_env("MLLM_BASE_URL"),
    mllm_api_key=get_required_env("MLLM_API_KEY"),
    mllm_model_name=get_required_env("MLLM_MODEL_NAME"),
)
