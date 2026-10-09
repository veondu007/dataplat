from fastapi import APIRouter, Depends

from app.core.response import ok
from app.core.security import get_current_user

router = APIRouter(prefix="/workspaces", tags=["workspace"])


@router.get("", dependencies=[Depends(get_current_user)])
def list_workspaces():
    return ok(
        [
            {
                "id": "ws-default",
                "name": "默认空间",
                "engine": "doris",
                "env": "dev",
            }
        ]
    )


@router.get("/me/doris-binding", dependencies=[Depends(get_current_user)])
def doris_binding():
    return ok(
        {
            "bound": False,
            "doris_user": None,
            "hint": "请绑定 Doris 个人账号后再执行查询与问数",
        }
    )
