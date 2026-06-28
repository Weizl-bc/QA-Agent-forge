import re
import shlex
from dataclasses import dataclass
from typing import Protocol, Sequence

from agent_core.common.env_config import get_env, get_required_env
from agent_core.models.prd.md_node import MdNode
from agent_core.models.prd.page_ref import PageRef


PAGE_REF_PATTERN = re.compile(
    r"<!--\s*qa:page-ref(?!-clear)\s*(?P<attributes>.*?)-->",
    flags=re.DOTALL,
)
PAGE_REF_CLEAR_PATTERN = re.compile(
    r"<!--\s*qa:page-ref-clear\s*-->",
)
PAGE_DIRECTIVE_PREFIX_PATTERN = re.compile(
    r"<!--\s*qa:page-ref",
)
LEGACY_PAGE_MARKER_PATTERN = re.compile(
    r"!(?:系统信息|页面信息)\s*[:：]",
)
PAGE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
ALLOWED_RELATIONS = {"primary", "related", "source", "target"}


class PageRefExtractionError(ValueError):
    """页面标签格式或作用范围不合法。"""


class PageRefResolutionError(PageRefExtractionError):
    """页面标签无法唯一解析为有效页面。"""


class PageRefDatabaseError(RuntimeError):
    """页面目录数据库配置或访问失败。"""


@dataclass(frozen=True)
class PageRefSpec:
    page_code: str
    relation_type: str = "primary"


@dataclass(frozen=True)
class PageCatalogEntry:
    page_id: int
    page_code: str
    page_name: str
    page_path: str | None
    system_id: int
    system_code: str | None
    system_name: str


class PageCatalogResolver(Protocol):
    def resolve_many(
        self,
        page_codes: Sequence[str],
    ) -> Sequence[PageCatalogEntry]:
        """批量返回有效页面；允许返回重复项供上层严格校验。"""


@dataclass(frozen=True)
class MySqlPageCatalogConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    connect_timeout_seconds: int

    @classmethod
    def from_env(cls) -> "MySqlPageCatalogConfig":
        try:
            port = int(get_env("MYSQL_PORT", "3306") or "3306")
            timeout = int(
                get_env("MYSQL_CONNECT_TIMEOUT_SECONDS", "5") or "5"
            )
        except ValueError as exc:
            raise PageRefDatabaseError(
                "MYSQL_PORT 和 MYSQL_CONNECT_TIMEOUT_SECONDS 必须是整数"
            ) from exc

        if port < 1 or timeout < 1:
            raise PageRefDatabaseError(
                "MYSQL_PORT 和 MYSQL_CONNECT_TIMEOUT_SECONDS 必须大于 0"
            )

        try:
            return cls(
                host=get_required_env("MYSQL_HOST"),
                port=port,
                user=get_required_env("MYSQL_USER"),
                password=get_required_env("MYSQL_PASSWORD"),
                database=get_required_env("MYSQL_DATABASE"),
                connect_timeout_seconds=timeout,
            )
        except ValueError as exc:
            raise PageRefDatabaseError(str(exc)) from exc


class MySqlPageCatalogResolver:
    """从 MySQL 页面目录批量解析 page_code。"""

    def __init__(
        self,
        config: MySqlPageCatalogConfig | None = None,
    ) -> None:
        self._config = config or MySqlPageCatalogConfig.from_env()

    def resolve_many(
        self,
        page_codes: Sequence[str],
    ) -> Sequence[PageCatalogEntry]:
        unique_codes = list(dict.fromkeys(page_codes))
        if not unique_codes:
            return []

        try:
            import pymysql
            from pymysql.cursors import DictCursor
        except ImportError as exc:
            raise PageRefDatabaseError(
                "缺少 PyMySQL 依赖，无法解析页面标签"
            ) from exc

        placeholders = ", ".join(["%s"] * len(unique_codes))
        query = f"""
            SELECT
                p.id AS page_id,
                p.page_code,
                p.page_name,
                p.page_path,
                s.id AS system_id,
                s.system_code,
                s.system_name
            FROM rag_page_source AS p
            INNER JOIN rag_system_source AS s
                ON s.id = p.system_id
               AND s.is_deleted = 0
            WHERE p.is_deleted = 0
              AND p.page_code IN ({placeholders})
        """

        connection = None
        try:
            connection = pymysql.connect(
                host=self._config.host,
                port=self._config.port,
                user=self._config.user,
                password=self._config.password,
                database=self._config.database,
                charset="utf8mb4",
                connect_timeout=self._config.connect_timeout_seconds,
                read_timeout=self._config.connect_timeout_seconds,
                write_timeout=self._config.connect_timeout_seconds,
                cursorclass=DictCursor,
                autocommit=True,
            )
            with connection.cursor() as cursor:
                cursor.execute(query, unique_codes)
                rows = cursor.fetchall()
        except pymysql.MySQLError as exc:
            raise PageRefDatabaseError(
                f"页面目录数据库访问失败：{type(exc).__name__}"
            ) from exc
        finally:
            if connection is not None:
                connection.close()

        return [
            PageCatalogEntry(
                page_id=int(row["page_id"]),
                page_code=str(row["page_code"]),
                page_name=str(row["page_name"]),
                page_path=(
                    str(row["page_path"])
                    if row["page_path"] is not None
                    else None
                ),
                system_id=int(row["system_id"]),
                system_code=(
                    str(row["system_code"])
                    if row["system_code"] is not None
                    else None
                ),
                system_name=str(row["system_name"]),
            )
            for row in rows
        ]


@dataclass
class _NodePageDirectives:
    node: MdNode
    clean_title: str
    clean_content: str
    specs: list[PageRefSpec]
    clears_inherited_refs: bool


def contains_page_directive(text: str) -> bool:
    """判断文本是否包含新页面指令或已废弃的旧页面标记。"""
    return bool(
        PAGE_DIRECTIVE_PREFIX_PATTERN.search(text)
        or LEGACY_PAGE_MARKER_PATTERN.search(text)
    )


def _parse_attributes(attributes: str) -> PageRefSpec:
    try:
        tokens = shlex.split(attributes, posix=True)
    except ValueError as exc:
        raise PageRefExtractionError(
            f"页面标签属性无法解析：{attributes.strip()}"
        ) from exc

    values: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            raise PageRefExtractionError(f"页面标签属性格式错误：{token}")
        name, value = token.split("=", 1)
        if name not in {"key", "relation"}:
            raise PageRefExtractionError(f"页面标签包含未知属性：{name}")
        if name in values:
            raise PageRefExtractionError(f"页面标签属性重复：{name}")
        values[name] = value.strip()

    page_code = values.get("key", "")
    if not page_code:
        raise PageRefExtractionError("页面标签缺少必填属性 key")
    if not PAGE_CODE_PATTERN.fullmatch(page_code):
        raise PageRefExtractionError(f"页面 key 格式非法：{page_code}")

    relation_type = values.get("relation", "primary")
    if relation_type not in ALLOWED_RELATIONS:
        raise PageRefExtractionError(
            f"页面 relation 非法：{relation_type}"
        )
    return PageRefSpec(page_code, relation_type)


def _extract_directives_from_text(
    text: str,
) -> tuple[str, list[PageRefSpec], bool]:
    if LEGACY_PAGE_MARKER_PATTERN.search(text):
        raise PageRefExtractionError(
            "检测到已废弃的 !系统信息/!页面信息 标记，请改用 "
            "<!-- qa:page-ref key=\"...\" -->"
        )

    specs = [
        _parse_attributes(match.group("attributes"))
        for match in PAGE_REF_PATTERN.finditer(text)
    ]
    clear_count = len(PAGE_REF_CLEAR_PATTERN.findall(text))
    cleaned = PAGE_REF_PATTERN.sub("", text)
    cleaned = PAGE_REF_CLEAR_PATTERN.sub("", cleaned)
    if PAGE_DIRECTIVE_PREFIX_PATTERN.search(cleaned):
        raise PageRefExtractionError("页面标签格式错误或标签未闭合")

    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned).strip()
    return cleaned, specs, clear_count > 0


def _collect_node_directives(root: MdNode) -> list[_NodePageDirectives]:
    directives: list[_NodePageDirectives] = []
    stack = [root]
    while stack:
        node = stack.pop()
        clean_title, title_specs, title_clear = _extract_directives_from_text(
            node.title
        )
        clean_content, content_specs, content_clear = (
            _extract_directives_from_text(node.content)
        )
        specs = list(
            dict.fromkeys([*title_specs, *content_specs])
        )
        clears = title_clear or content_clear
        if clears and specs:
            raise PageRefExtractionError(
                f"节点 {clean_title or node.id} 不能同时使用 page-ref 和 "
                "page-ref-clear"
            )
        directives.append(
            _NodePageDirectives(
                node=node,
                clean_title=clean_title,
                clean_content=clean_content,
                specs=specs,
                clears_inherited_refs=clears,
            )
        )
        stack.extend(reversed(node.children))
    return directives


def _resolve_catalog(
    specs: Sequence[PageRefSpec],
    resolver: PageCatalogResolver,
) -> dict[str, PageCatalogEntry]:
    requested_codes = list(dict.fromkeys(spec.page_code for spec in specs))
    entries = resolver.resolve_many(requested_codes)
    by_code: dict[str, list[PageCatalogEntry]] = {}
    for entry in entries:
        by_code.setdefault(entry.page_code, []).append(entry)

    missing_codes = [code for code in requested_codes if code not in by_code]
    if missing_codes:
        raise PageRefResolutionError(
            f"页面 key 不存在或页面/系统已删除：{', '.join(missing_codes)}"
        )

    duplicate_codes = [
        code for code, matches in by_code.items() if len(matches) != 1
    ]
    if duplicate_codes:
        raise PageRefResolutionError(
            f"页面 key 未保持唯一：{', '.join(duplicate_codes)}"
        )
    return {code: matches[0] for code, matches in by_code.items()}


def extract_page_refs(
    root: MdNode,
    resolver: PageCatalogResolver | None = None,
) -> None:
    """提取页面标签、批量解析页面目录，并按 MdNode 子树传播。"""
    directives = _collect_node_directives(root)
    all_specs = [spec for item in directives for spec in item.specs]
    catalog: dict[str, PageCatalogEntry] = {}
    if all_specs:
        catalog = _resolve_catalog(
            all_specs,
            resolver or MySqlPageCatalogResolver(),
        )

    directives_by_node_id = {id(item.node): item for item in directives}

    def visit(node: MdNode, inherited_refs: list[PageRef]) -> None:
        item = directives_by_node_id[id(node)]
        node.title = item.clean_title
        node.content = item.clean_content

        if item.clears_inherited_refs:
            active_refs: list[PageRef] = []
        elif item.specs:
            active_refs = []
            for spec in item.specs:
                entry = catalog[spec.page_code]
                active_refs.append(
                    PageRef(
                        page_id=entry.page_id,
                        page_code=entry.page_code,
                        page_name=entry.page_name,
                        page_path=entry.page_path,
                        system_id=entry.system_id,
                        system_code=entry.system_code,
                        system_name=entry.system_name,
                        relation_type=spec.relation_type,
                        confidence=1.0,
                        matched_by=[
                            "markdown_page_key",
                            "mysql_page_catalog",
                        ],
                    )
                )
        else:
            active_refs = [
                page_ref.model_copy(
                    update={
                        "matched_by": list(
                            dict.fromkeys(
                                [
                                    *page_ref.matched_by,
                                    "parent_inheritance",
                                ]
                            )
                        )
                    },
                    deep=True,
                )
                for page_ref in inherited_refs
            ]
        node.page_refs = active_refs

        for child in node.children:
            visit(child, active_refs)

    visit(root, [])
