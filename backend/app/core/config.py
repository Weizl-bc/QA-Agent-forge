"""Environment-backed backend configuration."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL


class Settings:
    """Validated runtime settings for the backend."""

    def __init__(self) -> None:
        import os

        load_dotenv(Path(__file__).resolve().parents[3] / ".env")
        required = ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise ValueError(f"缺少 MySQL 环境变量: {', '.join(missing)}")

        try:
            self.mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
            self.mysql_connect_timeout = int(
                os.getenv("MYSQL_CONNECT_TIMEOUT_SECONDS", "5")
            )
        except ValueError as exc:
            raise ValueError("MySQL 端口和连接超时必须是整数") from exc
        if self.mysql_port < 1 or self.mysql_connect_timeout < 1:
            raise ValueError("MySQL 端口和连接超时必须大于 0")

        self.mysql_url = URL.create(
            "mysql+pymysql",
            username=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASSWORD"],
            host=os.environ["MYSQL_HOST"],
            port=self.mysql_port,
            database=os.environ["MYSQL_DATABASE"],
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""
    return Settings()
