from fastapi import APIRouter

from app.core.response import ok
from app.modules.sql.guard import assert_readonly
from app.modules.sql.schemas import SqlPreviewRequest

router = APIRouter(prefix="/sql", tags=["sql"])


@router.post("/preview")
def preview(body: SqlPreviewRequest):
    assert_readonly(body.sql)
    return ok(
        {
            "accepted": True,
            "sql": body.sql,
            "message": "未绑定 Doris 个人账号时不会真实执行",
        }
    )
