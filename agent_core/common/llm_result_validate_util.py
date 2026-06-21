import json
import re
from typing import Any


def validate_llm_result_of_str(content: str | list[str | Any]) -> str:
    if isinstance(content, list):
        content = "\n".join(str(item) for item in content)

    return content


def extract_llm_content(result: Any) -> str:
    """兼容 LangChain AIMessage、字符串和分段文本内容。"""
    content = result.content if hasattr(result, "content") else result
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                text_parts.append(item["text"])
        return "\n".join(text_parts)
    return str(content)


def clean_llm_json_content(result: Any) -> str:
    """提取 LLM 文本并移除外围 Markdown JSON 代码块。"""
    content = extract_llm_content(result).strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content)
    return content.strip()


def parse_llm_string_list(result: Any, field_name: str) -> list[str]:
    """把 LLM 返回值解析为去重后的字符串数组。"""
    content = clean_llm_json_content(result)
    data = json.loads(content)
    if isinstance(data, dict):
        data = data.get(field_name)
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError(f"LLM 返回的 {field_name} 不是字符串数组: {content}")

    return list(dict.fromkeys(item.strip() for item in data if item.strip()))
