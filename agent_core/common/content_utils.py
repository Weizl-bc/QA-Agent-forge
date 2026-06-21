def remove_redundant_newlines(content: str) -> str:
    """
    删除 Markdown 内容中的空白行和行尾空格。

    保留有效内容之间的换行及每行开头的缩进，避免破坏 Markdown
    列表层级。兼容 ``\\n``、``\\r\\n`` 和 ``\\r`` 换行格式。
    """
    if not content:
        return ""

    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned_lines = [
        line.rstrip()
        for line in lines
        if line.strip()
    ]
    return "\n".join(cleaned_lines)
