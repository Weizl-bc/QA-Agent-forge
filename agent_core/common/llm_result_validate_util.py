from typing import Any


def validate_llm_result_of_str(content: str | list[str | Any]) -> str:
    if isinstance(content, list):
        content = "\n".join(str(item) for item in content)

    return content