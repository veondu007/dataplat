from fastapi import APIRouter

from app.core.response import ok

router = APIRouter(prefix="/workspaces", tags=["workspace"])


@router.get("")
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


@router.get("/me/doris-binding")
def doris_binding():
    return ok(
        {
            "bound": False,
            "doris_user": None,
            "hint": "请绑定 Doris 个人账号后再执行查询与问数",
        }
    )
