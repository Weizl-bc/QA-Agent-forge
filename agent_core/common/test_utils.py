import json
import re
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "log"


def write_json_string_to_log(
    json_content: str,
    prefix: str,
) -> Path:
    """
    将 JSON 字符串格式化后写入项目根目录的 ``log`` 文件夹。

    文件名格式：``{prefix}_{uuid}.json``。

    :param json_content: 合法的 JSON 格式字符串。
    :param prefix: 文件名前缀。
    :return: 已生成文件的绝对路径。
    :raises ValueError: prefix 为空或 JSON 字符串格式不合法。
    """
    if not prefix or not prefix.strip():
        raise ValueError("文件名前缀不能为空")

    safe_prefix = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", prefix.strip())
    safe_prefix = safe_prefix.strip("_")
    if not safe_prefix:
        raise ValueError("文件名前缀不包含有效字符")

    try:
        parsed_content = json.loads(json_content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 字符串格式不合法: {exc}") from exc

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    output_path = LOG_DIR / f"{safe_prefix}_{uuid4().hex}.json"
    output_path.write_text(
        json.dumps(
            parsed_content,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_path
