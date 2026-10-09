from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.response import ok
from app.core.security import get_current_user
from app.modules.sql.schemas import SqlPreviewRequest
from app.modules.sql.service import preview

router = APIRouter(prefix="/sql", tags=["sql"])


@router.post("/preview", dependencies=[Depends(get_current_user)])
def preview_endpoint(body: SqlPreviewRequest):
    return preview(body)


@router.get("/health", dependencies=[Depends(get_current_user)])
def doris_health():
    return ok(
        {
            "status": "ok",
            "doris": f"{settings.doris_host}:{settings.doris_port}/{settings.doris_database}",
        }
    )
