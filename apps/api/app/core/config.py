from pathlib import Path

from pydantic.fields import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    """向上查找仓库根目录（含 VERSION 文件的目录）。"""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "VERSION").is_file():
            return parent
    # 兜底：apps/api/app/core/config.py -> 仓库根
    return here.parents[4]


def _default_version() -> str:
    """产品版本单一来源：仓库根 VERSION 文件；读不到时回退骨架值。"""
    try:
        text = (_repo_root() / "VERSION").read_text(encoding="utf-8").strip()
        return text or "0.1.0-dev"
    except OSError:
        return "0.1.0-dev"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATAPLAT_", extra="ignore")

    env: str = "local"
    version: str = Field(default_factory=_default_version)
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    database_url: str = "postgresql+psycopg://dataplat:dataplat@127.0.0.1:5432/dataplat"
    redis_url: str = "redis://127.0.0.1:6379/0"
    jwt_secret: str = "change-me-change-me-change-me-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720  # 12 小时
    admin_user: str = "admin"
    admin_password: str = "admin123"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""

    # —— Doris 业务数据源（SQL 工作台 / AI 问数 的目标）——
    # 平台元数据仍存 PostgreSQL（database_url）；Doris 只承载用户业务表。
    # 本地集群见 deploy/doris/docker-compose.yml（2 FE + 2 BE，FE 查询端口 9030/9031）。
    doris_host: str = "127.0.0.1"
    doris_port: int = 9030
    doris_user: str = "root"
    doris_password: str = ""
    doris_database: str = "credit"
    doris_connect_timeout: int = 10  # 秒
    # Doris Stream Load HTTP 端口（FE HTTP，本地 compose 对外 8030），307 重定向到 BE
    doris_http_port: int = 8030


settings = Settings()
