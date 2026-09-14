from fastapi import APIRouter, Depends

from app.core.response import ok
from app.core.security import get_current_user

router = APIRouter(prefix="/assets", tags=["asset"])


@router.get("/overview", dependencies=[Depends(get_current_user)])
def overview():
    return ok(
        {
            "datasource_count": 0,
            "table_count": 0,
            "column_count": 0,
            "collector_healthy": True,
        }
    )


@router.get("/search", dependencies=[Depends(get_current_user)])
def search(q: str = ""):
    return ok({"keyword": q, "items": []})
