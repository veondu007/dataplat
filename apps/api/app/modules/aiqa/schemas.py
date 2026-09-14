from pydantic import BaseModel, Field


class AiqaAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2_000, description="自然语言问题")
    sql: str | None = Field(default=None, max_length=50_000, description="待确认执行的 SQL")
