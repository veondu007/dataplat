from fastapi import APIRouter, HTTPException

from app.core.response import ok
from app.modules.sql.guard import assert_readonly

router = APIRouter(prefix="/aiqa", tags=["aiqa"])


@router.post("/sessions")
def create_session():
    return ok({"id": "sess-demo", "title": "新对话"})


@router.post("/sessions/{session_id}/ask")
def ask(session_id: str, body: dict):
    question = (body or {}).get("question", "")
    sql = (body or {}).get("sql")
    if sql:
        try:
            assert_readonly(sql)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(
        {
            "session_id": session_id,
            "question": question,
            "tables": [],
            "sql": None,
            "needs_confirm": True,
            "message": "骨架接口：接入公有云模型后返回候选 SQL",
        }
    )
