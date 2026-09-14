from fastapi import APIRouter, HTTPException

from app.core.response import ok
from app.modules.sql.guard import assert_readonly

router = APIRouter(prefix="/sql", tags=["sql"])


@router.post("/preview")
def preview(body: dict):
    sql = (body or {}).get("sql", "")
    try:
        assert_readonly(sql)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(
        {
            "accepted": True,
            "sql": sql,
            "message": "未绑定 Doris 个人账号时不会真实执行",
        }
    )
