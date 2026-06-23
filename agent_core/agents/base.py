from abc import ABC, abstractmethod
from typing import Generic, TypeVar


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """所有 Agent 必须实现的抽象基类。"""

    @abstractmethod
    def run(self, input_data: InputT) -> OutputT:
        """执行 Agent 的核心任务并返回处理结果。"""
        raise NotImplementedError
