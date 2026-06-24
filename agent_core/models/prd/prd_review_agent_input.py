from pydantic import BaseModel


class PrdReviewAgentInput(BaseModel):

    input_path: str             # prd的路径（支持，相对路径、绝对路径、网络路径url）

    read_local_json: bool       # 是否读取本地的mdNode json文件