# agent_core/common/logging_config.py

import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import structlog

from agent_core.common.env_config import get_env


def _add_local_timestamp(
    logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """按配置的时区写入 ISO 8601 时间。"""
    timezone_name = get_env("LOG_TIMEZONE", "Asia/Shanghai")
    event_dict["timestamp"] = datetime.now(
        ZoneInfo(timezone_name)
    ).isoformat()
    return event_dict


def configure_logging(environment: str = "development") -> None:
    is_production = environment == "production"

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
        force=True,
    )

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        _add_local_timestamp,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if is_production
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            *shared_processors,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
