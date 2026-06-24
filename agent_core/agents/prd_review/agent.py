from agent_core.agents import BaseAgent
from agent_core.common.file_utils import read_md_file
from agent_core.common.json_utils import json_to_model
from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.prd_review_agent_input import PrdReviewAgentInput
from agent_core.models.prd.prd_review_agent_result import PrdReviewAgentResult
from agent_core.workflows.prd_cleaning_pipeline import PrdCleaningPipeline


class PrdPreviewAgent(BaseAgent[PrdReviewAgentInput, PrdReviewAgentResult]):
    """
    prd评审Agent
    """

    def run(self, input_data: PrdReviewAgentInput) -> PrdReviewAgentResult:
        result: PrdReviewAgentResult = PrdReviewAgentResult()

        md_node: MdNode

        if input_data.read_local_json:
            md_node = json_to_model(input_data.input_path, MdNode)
        else :
            context = PrdCleaningPipeline().run(input_data.input_path)
            md_node = context.root





        return result

