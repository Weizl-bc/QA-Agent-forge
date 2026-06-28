import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel


ModelT = TypeVar("ModelT", bound=BaseModel)


def _json_default(value: Any) -> Any:
    """将常见 Python 对象转换为可被 ``json.dumps`` 处理的数据。"""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (set, frozenset)):
        return list(value)
    if hasattr(value, "__dict__"):
        return {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    raise TypeError(
        f"{type(value).__name__} 对象无法转换为 JSON"
    )


def write_object_to_json(
    obj: Any,
    output_dir: str | Path,
    filename: str,
) -> Path:
    """
    将对象转换为 JSON，并写入 ``output_dir/filename.json``。

    ``output_dir`` 不存在时会自动创建。``filename`` 可以带或不带
    ``.json`` 后缀，但不能包含目录路径。

    :return: 生成文件的绝对路径
    :raises ValueError: 文件名为空或包含目录路径
    :raises TypeError: 对象中包含无法转换为 JSON 的值
    """
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("文件名不能为空")

    normalized_filename = filename.strip()
    if Path(normalized_filename).name != normalized_filename:
        raise ValueError("文件名不能包含目录路径")
    if normalized_filename.lower().endswith(".json"):
        normalized_filename = normalized_filename[:-5]
    if not normalized_filename:
        raise ValueError("文件名不能为空")

    directory = Path(output_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    output_path = (directory / f"{normalized_filename}.json").resolve()
    output_path.write_text(
        json.dumps(
            obj,
            ensure_ascii=False,
            indent=2,
            default=_json_default,
        ),
        encoding="utf-8",
    )
    return output_path


def json_to_model(json_string: str, model_class: type[ModelT]) -> ModelT:
    """
    将 JSON 字符串转换为指定的 Pydantic BaseModel 对象。

    :param json_string: 待转换的 JSON 字符串
    :param model_class: 目标 BaseModel 子类
    :return: model_class 对应的模型对象
    :raises TypeError: json_string 不是字符串，或 model_class 不是 BaseModel 子类
    :raises pydantic.ValidationError: JSON 格式错误或数据不符合模型定义
    """
    if not isinstance(json_string, str):
        raise TypeError("json_string 必须是字符串")

    if not isinstance(model_class, type) or not issubclass(model_class, BaseModel):
        raise TypeError("model_class 必须是 BaseModel 子类")

    return model_class.model_validate_json(json_string)
