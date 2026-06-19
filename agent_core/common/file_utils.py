from pathlib import Path


def read_md_file(input_path: str) -> list[str]:
    """
    读取md文件，并把它转换为字符串，并且字符串以\n分割
    :param input_path: 绝对地址
    :return: 以\n分割后的字符串数组
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{input_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件：{input_path}")

    content = path.read_text(encoding="utf-8")
    return content.split("\n")

