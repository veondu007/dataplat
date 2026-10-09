"""资产模块路由：数据地图(总览/浏览/详情/检索)+ Doris 元数据同步触发与轮询。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.core.security import get_current_user
from app.modules.asset import service

router = APIRouter(prefix="/assets", tags=["asset"])
_auth = [Depends(get_current_user)]


@router.get("/overview", dependencies=_auth)
def overview(db: Session = Depends(get_db)):
    return ok(service.get_overview(db))


@router.get("/search", dependencies=_auth)
def search(q: str = "", db: Session = Depends(get_db)):
    return ok(service.search_tables(db, q))


@router.get("/databases", dependencies=_auth)
def databases(db: Session = Depends(get_db)):
    return ok(service.list_databases(db))


@router.get("/databases/{database_name}/tables", dependencies=_auth)
def tables(database_name: str, db: Session = Depends(get_db)):
    return ok(service.list_tables_by_db(db, database_name))


@router.get("/tables/{table_id}", dependencies=_auth)
def table_detail(table_id: str, db: Session = Depends(get_db)):
    return ok(service.get_table_detail(db, table_id))


@router.post("/sync", dependencies=_auth)
def sync():
    job_id = service.sync_service.run_async()
    return ok({"job_id": job_id, "status": "running"})


@router.get("/sync/{job_id}", dependencies=_auth)
def sync_status(job_id: str):
    job = service.sync_service.get_status(job_id)
    if job is None:
        from app.core.exceptions import ApiError, ErrorCode

        raise ApiError(ErrorCode.NOT_FOUND, f"同步任务不存在（可能因服务重启丢失）: {job_id}", status_code=404)
    return ok(service.job_to_dict(job))