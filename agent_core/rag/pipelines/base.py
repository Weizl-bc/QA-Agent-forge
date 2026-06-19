from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

class InputType(Enum):
    """
    RAG流水线的输入类型
    """

    # PRD类型
    MD = "md"

class PipelineType(Enum):
    """
    流水线的类型
    """

    PRD = "prd"

class BasePipeline(ABC):
    """
    RAG流水线抽象类
    """

    def write_vector(slf, pipeline_type: PipelineType, input_path: str, input_type: InputType):
        """

        :param input_path:
        :param input_type:
        :return:
        """

        if pipeline_type == PipelineType.PRD:
            return slf.run(value=slf._parser_input(input_path, input_type))

        pass

    def _parser_input(self, input_path: str, input_type: InputType):

        return ""

    @abstractmethod
    def run(self, value: Any):
        pass