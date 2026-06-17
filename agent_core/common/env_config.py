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
    llm_chat_model_name: str
    llm_base_url: str
    llm_api_key: str


settings = Settings(
    llm_chat_model_name=get_required_env("LLM_CHAT_MODEL_NAME"),
    llm_base_url=get_required_env("LLM_BASE_URL"),
    llm_api_key=get_required_env("LLM_API_KEY"),
)