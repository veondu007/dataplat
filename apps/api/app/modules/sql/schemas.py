from pydantic import BaseModel, Field


class SqlPreviewRequest(BaseModel):
    sql: str = Field(..., min_length=1, max_length=50_000, description="只读 SQL")
