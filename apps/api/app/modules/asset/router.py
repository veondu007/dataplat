"""资产模块路由：数据地图(总览/浏览/详情/检索)+ 统计 + 血缘/标签 + 元数据同步。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.core.security import get_current_user
from app.modules.asset import service

router = APIRouter(prefix="/assets", tags=["asset"])
_auth = [Depends(get_current_user)]


class LineageIn(BaseModel):
    related_table_id: str
    direction: str = Field(pattern="^(upstream|downstream)$")
    edge_type: str = "manual"
    note: str | None = None


class TagIn(BaseModel):
    tag: str = Field(min_length=1, max_length=64)


TagName = Annotated[str, StringConstraints(min_length=1, max_length=64)]


@router.get("/overview", dependencies=_auth)
def overview(db: Session = Depends(get_db)):
    return ok(service.get_overview(db))


@router.get("/search", dependencies=_auth)
def search(q: str = "", db: Session = Depends(get_db)):
    return ok(service.search_tables(db, q))


@router.get("/stats", dependencies=_auth)
def stats(db: Session = Depends(get_db)):
    return ok(service.get_stats(db))


@router.get("/tags", dependencies=_auth)
def tags(db: Session = Depends(get_db)):
    return ok(service.list_tags(db))


@router.get("/tables/{table_id}/lineage", dependencies=_auth)
def table_lineage(table_id: str, db: Session = Depends(get_db)):
    return ok(service.get_table_lineage(db, table_id))


@router.post("/tables/{table_id}/lineage", dependencies=_auth)
def add_table_lineage(table_id: str, body: LineageIn, db: Session = Depends(get_db)):
    return ok(
        service.add_lineage(db, table_id, body.related_table_id, body.direction, body.edge_type, body.note)
    )


@router.delete("/tables/{table_id}/lineage/{lineage_id}", dependencies=_auth)
def remove_table_lineage(lineage_id: str, db: Session = Depends(get_db)):
    return ok(service.remove_lineage(db, lineage_id))


@router.get("/tables/{table_id}/tags", dependencies=_auth)
def table_tags(table_id: str, db: Session = Depends(get_db)):
    return ok(service.get_table_tags(db, table_id))


@router.post("/tables/{table_id}/tags", dependencies=_auth)
def add_table_tag(table_id: str, body: TagIn, db: Session = Depends(get_db)):
    return ok(service.add_table_tag(db, table_id, body.tag))


@router.delete("/tables/{table_id}/tags/{tag}", dependencies=_auth)
def remove_table_tag(table_id: str, tag: TagName, db: Session = Depends(get_db)):
    return ok(service.remove_table_tag(db, table_id, tag))


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