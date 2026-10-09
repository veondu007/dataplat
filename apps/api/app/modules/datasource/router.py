"""数据源模块路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.core.security import get_current_user
from app.modules.datasource import service
from app.modules.datasource.schemas import DatasourceCreate, DatasourceUpdate, SyncRequest, TestConnection

router = APIRouter(prefix="/datasources", tags=["datasource"])
_auth = [Depends(get_current_user)]


@router.get("", dependencies=_auth)
def list_sources(db: Session = Depends(get_db)):
    return ok(service.list_sources(db))


@router.post("", dependencies=_auth)
def create_source(body: DatasourceCreate, db: Session = Depends(get_db)):
    return ok(service.create_source(db, body))


@router.get("/{datasource_id}", dependencies=_auth)
def get_source(datasource_id: str, db: Session = Depends(get_db)):
    return ok(service.get_source(db, datasource_id))


@router.put("/{datasource_id}", dependencies=_auth)
def update_source(datasource_id: str, body: DatasourceUpdate, db: Session = Depends(get_db)):
    return ok(service.update_source(db, datasource_id, body))


@router.delete("/{datasource_id}", dependencies=_auth)
def delete_source(datasource_id: str, db: Session = Depends(get_db)):
    return ok(service.delete_source(db, datasource_id))


@router.post("/{datasource_id}/test", dependencies=_auth)
def test_source(datasource_id: str, body: TestConnection | None = None, db: Session = Depends(get_db)):
    return ok(service.test_source(db, datasource_id, body))


@router.get("/{datasource_id}/tables", dependencies=_auth)
def list_tables(datasource_id: str, db: Session = Depends(get_db)):
    return ok(service.list_tables(db, datasource_id))


@router.post("/{datasource_id}/sync", dependencies=_auth)
def start_sync(datasource_id: str, body: SyncRequest, db: Session = Depends(get_db)):
    return ok(service.start_sync(db, datasource_id, body))


@router.post("/{datasource_id}/sync-xlsx", dependencies=_auth)
async def start_sync_xlsx(
    datasource_id: str,
    file: UploadFile = File(...),
    sheet_name: str | None = Form(default=None),
    target_table: str | None = Form(default=None),
    column_types: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    col_types = _parse_col_types(column_types)
    return ok(await run_in_threadpool(service.start_sync_xlsx, db, datasource_id, file, sheet_name, target_table, col_types))


@router.post("/xlsx/parse", dependencies=_auth)
async def parse_xlsx(file: UploadFile = File(...)):
    return ok(await run_in_threadpool(service.parse_xlsx, file))


@router.get("/sync/jobs", dependencies=_auth)
def list_jobs(datasource_id: str = Query(..., min_length=1)):
    return ok(service.list_jobs(datasource_id))


@router.get("/sync/{job_id}", dependencies=_auth)
def get_sync_status(job_id: str):
    return ok(service.get_sync_status(job_id))


@router.post("/sync/{job_id}/retry", dependencies=_auth)
def retry_sync(job_id: str, db: Session = Depends(get_db)):
    return ok(service.retry_sync(db, job_id))


def _parse_col_types(raw: str | None) -> dict | None:
    """把前端传来的 `{col: doris_type}` JSON 字符串解析为 dict；None 则返回 None。"""
    import json

    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        return None
    except (json.JSONDecodeError, TypeError):
        return None