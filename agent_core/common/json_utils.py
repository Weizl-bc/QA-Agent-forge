from typing import TypeVar

from pydantic import BaseModel


ModelT = TypeVar("ModelT", bound=BaseModel)


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
