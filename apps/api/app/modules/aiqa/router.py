from fastapi import APIRouter, Depends

from app.core.response import ok
from app.core.security import get_current_user
from app.modules.aiqa.schemas import AiqaAskRequest
from app.modules.sql.guard import assert_readonly

router = APIRouter(prefix="/aiqa", tags=["aiqa"])


@router.post("/sessions", dependencies=[Depends(get_current_user)])
def create_session():
    return ok({"id": "sess-demo", "title": "新对话"})


@router.post("/sessions/{session_id}/ask", dependencies=[Depends(get_current_user)])
def ask(session_id: str, body: AiqaAskRequest):
    if body.sql:
        assert_readonly(body.sql)
    return ok(
        {
            "session_id": session_id,
            "question": body.question,
            "tables": [],
            "sql": None,
            "needs_confirm": True,
            "message": "骨架接口：接入公有云模型后返回候选 SQL",
        }
    )
