from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATAPLAT_", extra="ignore")

    env: str = "local"
    version: str = "0.1.0-dev"
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    database_url: str = "postgresql+psycopg://dataplat:dataplat@127.0.0.1:5432/dataplat"
    redis_url: str = "redis://127.0.0.1:6379/0"
    jwt_secret: str = "change-me"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""


settings = Settings()
