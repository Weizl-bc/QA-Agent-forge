from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen


def read_md_file(input_path: str) -> list[str]:
    """
    读取 Markdown 文件，并按换行符分割内容。

    支持相对路径、绝对路径以及 HTTP/HTTPS 网络路径。

    :param input_path: 本地文件路径或 HTTP/HTTPS URL
    :return: 以 ``\n`` 分割后的字符串数组
    """
    if not isinstance(input_path, str) or not input_path.strip():
        raise ValueError("文件路径不能为空")

    parsed_url = urlparse(input_path)
    if parsed_url.scheme.lower() in {"http", "https"}:
        with urlopen(input_path, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            content = response.read().decode(charset)
        return content.split("\n")

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{input_path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件：{input_path}")

    content = path.read_text(encoding="utf-8")
    return content.split("\n")
