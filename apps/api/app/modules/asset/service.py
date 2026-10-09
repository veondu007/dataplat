"""资产同步服务：连接 Doris 采集元数据,UPSERT 到 tables/columns,软删 + 东八区时区。"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.exceptions import ApiError, ErrorCode
from app.models import Column, Datasource, Table
from app.modules.asset.collector import DorisMetadataConnector

logger = logging.getLogger(__name__)

CN_TZ = ZoneInfo("Asia/Shanghai")

# 全局 Doris 数据源的固定 id(asset 展示层按 datasource_id 过滤)
DORIS_DATASOURCE_ID = "ds_doris"


def now_cn() -> datetime:
    """当前东八区时间(带 tz),供入库时间戳使用。"""
    return datetime.now(CN_TZ)


def _ensure_doris_datasource(db: Session) -> str:
    """确保存在全局 Doris 数据源行(采集绑定目标),返回其 id。"""
    ds = db.get(Datasource, DORIS_DATASOURCE_ID)
    if ds is None:
        ds = Datasource(
            id=DORIS_DATASOURCE_ID,
            workspace_id="ws-default",
            name="Doris（内置）",
            engine="doris",
        )
        db.add(ds)
        db.commit()
    return DORIS_DATASOURCE_ID


# —— UPSERT(PostgreSQL ON CONFLICT,等价 MySQL ON DUPLICATE KEY UPDATE) ——

# —— 采集批号 ——

def _new_sync_version() -> int:
    return int(datetime.now(CN_TZ).timestamp())


# —— 同步服务(单例 + 后台线程) ——

@dataclass
class AssetSyncJob:
    job_id: str
    status: str = "pending"  # pending/running/success/failed
    error_message: str | None = None
    items: dict = field(default_factory=dict)  # {databases, tables, columns}
    started_at: str | None = None
    finished_at: str | None = None


class AssetSyncService:
    def __init__(self) -> None:
        self._job: AssetSyncJob | None = None
        self._lock = threading.Lock()

    def run_async(self) -> str:
        """后台线程执行完整同步,返回 job_id 供轮询。"""
        job = AssetSyncJob(job_id=uuid.uuid4().hex, status="running")
        job.started_at = datetime.now(CN_TZ).isoformat(timespec="seconds")
        with self._lock:
            self._job = job
        t = threading.Thread(
            target=self._run_job, args=(job,), name=f"asset-sync-{job.job_id[:8]}", daemon=True
        )
        t.start()
        return job.job_id

    def get_status(self, job_id: str) -> AssetSyncJob | None:
        with self._lock:
            job = self._job
        if job and job.job_id == job_id:
            return job
        return None

    def _run_job(self, job: AssetSyncJob) -> None:
        try:
            counts = self.sync_all()
            job.items = counts
            job.status = "success"
        except Exception as exc:  # noqa: BLE001
            logger.exception("asset sync failed")
            job.status = "failed"
            job.error_message = str(exc)
        finally:
            job.finished_at = datetime.now(CN_TZ).isoformat(timespec="seconds")

    def sync_all(self) -> dict:
        """采集所有库表并 UPSERT,返回统计。每个 database 一个事务。"""
        connector = DorisMetadataConnector(
            host=settings.doris_host,
            port=settings.doris_port,
            user=settings.doris_user,
            password=settings.doris_password,
            database=settings.doris_database,
        )
        sync_version = _new_sync_version()
        databases = connector.list_databases()

        n_tables = n_columns = 0
        with SessionLocal() as db:
            datasource_id = _ensure_doris_datasource(db)

            for db_name in databases:
                try:
                    tables = connector.list_tables(db_name)
                except Exception as exc:  # noqa: BLE001 - 单库失败不阻断整体
                    logger.warning("list_tables(%s) failed: %s", db_name, exc)
                    continue
                with SessionLocal() as db_t:
                    for t in tables:
                        db_t.execute(
                            pg_insert(Table).values(
                                id=f"t_{uuid.uuid4().hex[:12]}",
                                datasource_id=datasource_id,
                                database_name=db_name,
                                name=t["name"],
                                comment=t.get("comment"),
                                num_rows=t.get("num_rows"),
                                data_size=t.get("data_size"),
                                engine=t.get("engine"),
                                partition_cols=None,
                                is_deleted=False,
                                sync_version=sync_version,
                                last_synced_at=now_cn(),
                            ).on_conflict_do_update(
                                index_elements=[Table.datasource_id, Table.database_name, Table.name],
                                set_={
                                    "comment": pg_insert(Table).excluded.comment,
                                    "num_rows": pg_insert(Table).excluded.num_rows,
                                    "data_size": pg_insert(Table).excluded.data_size,
                                    "engine": pg_insert(Table).excluded.engine,
                                    "is_deleted": False,
                                    "sync_version": sync_version,
                                    "last_synced_at": now_cn(),
                                },
                            )
                        )
                        n_tables += 1
                        table_row = db_t.execute(
                            select(Table).where(
                                Table.datasource_id == datasource_id,
                                Table.database_name == db_name,
                                Table.name == t["name"],
                            )
                        ).scalar_one_or_none()
                        if table_row is None:
                            continue
                        cols = connector.list_columns(db_name, t["name"])
                        for c in cols:
                            db_t.execute(
                                pg_insert(Column).values(
                                    id=f"c_{uuid.uuid4().hex[:12]}",
                                    table_id=table_row.id,
                                    name=c["name"],
                                    data_type=c["data_type"],
                                    position=c["position"],
                                    is_partition=c.get("is_partition", False),
                                    comment=c.get("comment"),
                                    is_deleted=False,
                                    sync_version=sync_version,
                                ).on_conflict_do_update(
                                    index_elements=[Column.table_id, Column.name],
                                    set_={
                                        "data_type": pg_insert(Column).excluded.data_type,
                                        "position": pg_insert(Column).excluded.position,
                                        "is_partition": pg_insert(Column).excluded.is_partition,
                                        "comment": pg_insert(Column).excluded.comment,
                                        "is_deleted": False,
                                        "sync_version": sync_version,
                                    },
                                )
                            )
                            n_columns += 1
                    db_t.commit()
            db.commit()

        # 软删:本轮未采集到的表(旧批号)及其列标 is_deleted=1
        with SessionLocal() as db_clean:
            _soft_delete_stale_tables(db_clean, datasource_id, sync_version)
            _soft_delete_stale_columns(db_clean, sync_version)

        return {"databases": len(databases), "tables": n_tables, "columns": n_columns}


def _soft_delete_stale_tables(db: Session, datasource_id: str, sync_version: int) -> None:
    """本次未 upsert 到的表(旧批号)标 is_deleted=1。"""
    db.execute(
        update(Table)
        .where(
            Table.datasource_id == datasource_id,
            Table.sync_version.isnot(None),
            Table.sync_version != sync_version,
            Table.is_deleted.is_(False),
        )
        .values(is_deleted=True)
    )
    db.commit()


def _soft_delete_stale_columns(db: Session, sync_version: int) -> None:
    """本次未 upsert 到的列(旧批号)标 is_deleted=1。"""
    db.execute(
        update(Column)
        .where(
            Column.sync_version.isnot(None),
            Column.sync_version != sync_version,
            Column.is_deleted.is_(False),
        )
        .values(is_deleted=True)
    )
    db.commit()


# 单例
sync_service = AssetSyncService()


def job_to_dict(job: AssetSyncJob) -> dict:
    return {
        "job_id": job.job_id,
        "status": job.status,
        "error_message": job.error_message,
        "items": job.items,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


__all__ = [
    "now_cn",
    "AssetSyncService",
    "sync_service",
    "job_to_dict",
    "DORIS_DATASOURCE_ID",
]


# —— 资产查询(供 router/展示) ——

def get_overview(db: Session) -> dict:
    from sqlalchemy import distinct, func

    t_count = db.execute(
        select(func.count()).select_from(Table).where(Table.is_deleted.is_(False))
    ).scalar()
    c_count = db.execute(
        select(func.count()).select_from(Column).where(Column.is_deleted.is_(False))
    ).scalar()
    ds_count = db.execute(select(func.count()).select_from(Datasource)).scalar()
    db_count = db.execute(
        select(func.count(distinct(Table.database_name))).where(Table.is_deleted.is_(False))
    ).scalar()
    return {
        "datasource_count": ds_count or 0,
        "database_count": db_count or 0,
        "table_count": t_count or 0,
        "column_count": c_count or 0,
        "collector_healthy": True,  # P0 占位;失败由 job 状态反映
    }


def list_databases(db: Session) -> list[str]:
    from sqlalchemy import distinct

    rows = db.execute(
        select(distinct(Table.database_name))
        .where(Table.is_deleted.is_(False))
        .order_by(Table.database_name)
    ).scalars().all()
    return list(rows)


def list_tables_by_db(db: Session, database_name: str) -> list[dict]:
    rows = db.execute(
        select(Table)
        .where(Table.is_deleted.is_(False), Table.database_name == database_name)
        .order_by(Table.name)
    ).scalars().all()
    return [
        {
            "id": t.id,
            "database_name": t.database_name,
            "name": t.name,
            "comment": t.comment,
            "num_rows": t.num_rows,
            "data_size": t.data_size,
            "engine": t.engine,
            "partition_cols": t.partition_cols,
            "last_synced_at": t.last_synced_at.isoformat() if t.last_synced_at else None,
        }
        for t in rows
    ]


def get_table_detail(db: Session, table_id: str) -> dict:
    t = db.get(Table, table_id)
    if t is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"表不存在: {table_id}", status_code=404)
    cols = db.execute(
        select(Column)
        .where(Column.table_id == table_id, Column.is_deleted.is_(False))
        .order_by(Column.position)
    ).scalars().all()
    return {
        "id": t.id,
        "datasource_id": t.datasource_id,
        "database_name": t.database_name,
        "name": t.name,
        "comment": t.comment,
        "num_rows": t.num_rows,
        "data_size": t.data_size,
        "engine": t.engine,
        "partition_cols": t.partition_cols,
        "last_synced_at": t.last_synced_at.isoformat() if t.last_synced_at else None,
        "columns": [
            {
                "name": c.name,
                "data_type": c.data_type,
                "position": c.position,
                "is_partition": c.is_partition,
                "comment": c.comment,
            }
            for c in cols
        ],
    }


def search_tables(db: Session, q: str) -> list[dict]:
    """按表名/库名/注释(及列名)模糊检索。"""
    from sqlalchemy import or_

    keyword = f"%{q or ''}%"
    rows = db.execute(
        select(Table)
        .where(
            Table.is_deleted.is_(False),
            or_(
                Table.name.ilike(keyword),
                Table.database_name.ilike(keyword),
                Table.comment.ilike(keyword),
            ),
        )
        .order_by(Table.name)
        .limit(100)
    ).scalars().all()
    return [
        {
            "id": t.id,
            "database_name": t.database_name,
            "name": t.name,
            "comment": t.comment,
            "num_rows": t.num_rows,
            "data_size": t.data_size,
            "engine": t.engine,
        }
        for t in rows
    ]