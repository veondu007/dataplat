from fastapi import APIRouter

from app.core.response import ok

router = APIRouter(prefix="/assets", tags=["asset"])


@router.get("/overview")
def overview():
    return ok(
        {
            "datasource_count": 0,
            "table_count": 0,
            "column_count": 0,
            "collector_healthy": True,
        }
    )


@router.get("/search")
def search(q: str = ""):
    return ok({"keyword": q, "items": []})
