"""数据源模块服务层：CRUD、连通测试、表列举、同步触发、xlsx 解析。"""

from __future__ import annotations

import os
import tempfile
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ApiError, ErrorCode
from app.models import Datasource, DatasourceConn
from app.modules.datasource import guard
from app.modules.datasource.sync import registry
from app.modules.datasource.sync.registry import build_config, new_job_id
from app.modules.datasource.sync.engines import MaxComputeEngine, MySQLEngine, XlsxEngine

_XLSX_DIR = os.path.join(tempfile.gettempdir(), "dataplat_xlsx")
os.makedirs(_XLSX_DIR, exist_ok=True)


# —— 配置拆分：conn_meta（非敏感）/ credentials（敏感） ——

def _split_config(engine: str, data) -> tuple[dict, dict]:
    """按引擎把通用字段拆成 conn_meta 与 credentials。"""
    if engine == "mysql":
        meta = {"host": data.host, "port": data.port, "database": data.database}
        cred = {"user": data.user, "password": data.password}
        if not (meta["host"] and cred.get("user")):
            raise ApiError(ErrorCode.VALIDATION, "MySQL 数据源需提供 host 与 user", status_code=400)
        return _strip_none(meta), _strip_none(cred)
    if engine == "maxcompute":
        meta = {"endpoint": data.endpoint, "project": data.project, "jar_path": data.jar_path}
        cred = {"access_id": data.access_id, "access_key": data.access_key}
        if not (meta.get("endpoint") and meta.get("project") and cred.get("access_id")):
            raise ApiError(ErrorCode.VALIDATION, "MaxCompute 数据源需提供 endpoint / project / access_id", status_code=400)
        return _strip_none(meta), _strip_none(cred)
    if engine == "xlsx":
        # xlsx 无需连接字段；连接信息在 sync-xlsx 上传时写入 file_path
        return {}, {}
    raise ApiError(ErrorCode.VALIDATION, f"unknown engine {engine}", status_code=400)


def _strip_none(d: dict) -> dict:
    return {k: v for k, v in d.items() if k is not None and v is not None}


def make_engine(engine: str, meta: dict, cred: dict):
    guard.assert_valid_engine(engine)
    if engine == "mysql":
        return MySQLEngine(meta or {}, cred or {})
    if engine == "maxcompute":
        return MaxComputeEngine(meta or {}, cred or {})
    if engine == "xlsx":
        return XlsxEngine(meta or {}, cred or {})
    raise ApiError(ErrorCode.VALIDATION, f"unknown engine {engine}", status_code=400)


def _row(db: Session, datasource_id: str) -> Datasource:
    ds = db.get(Datasource, datasource_id)
    if ds is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"数据源不存在: {datasource_id}", status_code=404)
    return ds


def _mask(cred: dict | None) -> dict | None:
    """凭证掩码后返回（不泄露明文），命中的键用 **** 替换。"""
    if not cred:
        return None
    return {k: ("****" if v is not None else None) for k, v in cred.items()}


def get_conn(db: Session, datasource_id: str) -> DatasourceConn:
    ds = _row(db, datasource_id)
    if ds.conn is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"数据源未配置连接信息: {datasource_id}", status_code=400)
    return ds.conn


# —— CRUD ——

def list_sources(db: Session) -> list[dict]:
    rows = db.execute(select(Datasource).order_by(Datasource.created_at.desc())).scalars().all()
    out = []
    for ds in rows:
        out.append(
            {
                "id": ds.id,
                "workspace_id": ds.workspace_id,
                "name": ds.name,
                "engine": ds.engine,
                "conn_meta": ds.conn.conn_meta if ds.conn else None,
                "credentials": _mask(ds.conn.credentials if ds.conn else None),
                "created_at": ds.created_at.isoformat() if ds.created_at else None,
            }
        )
    return out


def create_source(db: Session, data) -> dict:
    guard.assert_valid_engine(data.engine)
    ds = Datasource(
        id=f"ds_{uuid.uuid4().hex[:12]}",
        workspace_id=data.workspace_id,
        name=data.name,
        engine=data.engine,
    )
    meta, cred = _split_config(data.engine, data)
    if data.engine != "xlsx":
        conn = DatasourceConn(
            id=f"c_{uuid.uuid4().hex[:12]}",
            datasource_id=ds.id,
            conn_meta=meta,
            credentials=cred,
        )
        ds.conn = conn
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return {
        "id": ds.id,
        "workspace_id": ds.workspace_id,
        "name": ds.name,
        "engine": ds.engine,
        "conn_meta": ds.conn.conn_meta if ds.conn else None,
    }


def get_source(db: Session, datasource_id: str) -> dict:
    ds = _row(db, datasource_id)
    return {
        "id": ds.id,
        "workspace_id": ds.workspace_id,
        "name": ds.name,
        "engine": ds.engine,
        "conn_meta": ds.conn.conn_meta if ds.conn else None,
        "credentials": _mask(ds.conn.credentials if ds.conn else None),
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
    }


def update_source(db: Session, datasource_id: str, data) -> dict:
    ds = _row(db, datasource_id)
    guard.assert_valid_engine(data.engine)
    ds.name = data.name
    ds.engine = data.engine
    meta, cred = _split_config(data.engine, data)
    if data.engine != "xlsx":
        if ds.conn is None:
            ds.conn = DatasourceConn(
                id=f"c_{uuid.uuid4().hex[:12]}",
                datasource_id=ds.id,
                conn_meta=meta,
                credentials=cred,
            )
        else:
            # 未填写的字段保留原值，避免覆盖已有连接
            if meta:
                ds.conn.conn_meta = {**(ds.conn.conn_meta or {}), **meta}
            if cred:
                ds.conn.credentials = {**(ds.conn.credentials or {}), **cred}
    db.commit()
    return {"id": ds.id, "updated": True}


def delete_source(db: Session, datasource_id: str) -> dict:
    ds = _row(db, datasource_id)
    db.delete(ds)
    db.commit()
    return {"id": datasource_id, "deleted": True}


# —— 连通测试 ——

def test_source(db: Session, datasource_id: str, body) -> dict:
    ds = _row(db, datasource_id)
    meta = ds.conn.conn_meta if ds.conn else {}
    cred = ds.conn.credentials if ds.conn else {}
    if body and body.conn_meta is not None:
        meta = {**meta, **body.conn_meta}
    if body and body.credentials is not None:
        cred = {**cred, **body.credentials}
    engine = make_engine(ds.engine, meta, cred)
    return engine.test_conn()


def list_tables(db: Session, datasource_id: str) -> list[dict]:
    conn = get_conn(db, datasource_id)
    engine = make_engine(conn.datasource.engine, conn.conn_meta or {}, conn.credentials or {})
    tables = engine.list_tables()
    return [{"database_name": t.database_name, "name": t.name, "comment": t.comment} for t in tables]


# —— 同步 ——

def start_sync(db: Session, datasource_id: str, body) -> dict:
    ds = _row(db, datasource_id)
    conn = get_conn(db, datasource_id)
    guard.assert_valid_engine(ds.engine)
    if ds.engine == "xlsx":
        raise ApiError(ErrorCode.VALIDATION, "XLSX 请通过 /sync-xlsx 上传文件同步", status_code=400)

    source = body.source_table
    if not source:
        raise ApiError(ErrorCode.VALIDATION, "缺少源表 source_table", status_code=400)
    target_table = body.target_table or source
    guard.assert_target_table(target_table)
    target_db = body.target_database or settings.doris_database
    guard.assert_target_database(target_db)

    engine = make_engine(ds.engine, conn.conn_meta or {}, conn.credentials or {})
    config = build_config(
        datasource_id=datasource_id,
        engine_type=ds.engine,
        source=source,
        target_database=target_db,
        target_table=target_table,
        max_retries=body.max_retries,
        truncate=body.truncate,
        engine=engine,
    )
    state = registry.registry.submit(config)
    return {"job_id": config.job_id, "status": state.status}


def start_sync_xlsx(db: Session, datasource_id: str, file, sheet_name: str | None, target_table: str | None, column_types: dict | None) -> dict:
    """上传 xlsx 文件并触发同步。文件写入临时目录，file_path 存入 conn。"""
    ds = _row(db, datasource_id)
    if ds.engine != "xlsx":
        raise ApiError(ErrorCode.VALIDATION, "sync-xlsx 仅用于 xlsx 数据源", status_code=400)

    if file is None or not file.filename:
        raise ApiError(ErrorCode.VALIDATION, "缺少 xlsx 文件", status_code=400)
    if not file.filename.lower().endswith(".xlsx"):
        raise ApiError(ErrorCode.VALIDATION, "仅支持 .xlsx 文件", status_code=400)

    file_path = _save_upload(file)
    meta = {"file_path": file_path}
    cred = {}
    if ds.conn is None:
        ds.conn = DatasourceConn(
            id=f"c_{uuid.uuid4().hex[:12]}",
            datasource_id=ds.id,
            conn_meta=meta,
            credentials=cred,
        )
    else:
        ds.conn.conn_meta = {**(ds.conn.conn_meta or {}), **meta}
    db.commit()

    engine = XlsxEngine(meta, cred)
    if sheet_name:
        sheets = [s.name for s in engine.list_tables()]
        if sheet_name not in sheets:
            raise ApiError(ErrorCode.VALIDATION, f"工作簿无此工作表: {sheet_name}", status_code=400)
    target_table = target_table or (sheet_name or "xlsx_import")
    guard.assert_target_table(target_table)
    target_db = settings.doris_database

    config = build_config(
        datasource_id=datasource_id,
        engine_type="xlsx",
        source=sheet_name or engine.list_tables()[0].name,
        target_database=target_db,
        target_table=target_table,
        max_retries=2,
        truncate=True,
        column_overrides=column_types,
        engine=engine,
    )
    state = registry.registry.submit(config)
    return {"job_id": config.job_id, "status": state.status}


def _save_upload(file) -> str:
    fname = f"{uuid.uuid4().hex}.xlsx"
    path = os.path.join(_XLSX_DIR, fname)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path


def parse_xlsx(file) -> dict:
    """解析上传的 xlsx，返回各 sheet 的列（推断类型）+ 行数预览。"""
    if file is None or not file.filename:
        raise ApiError(ErrorCode.VALIDATION, "缺少 xlsx 文件", status_code=400)
    if not file.filename.lower().endswith(".xlsx"):
        raise ApiError(ErrorCode.VALIDATION, "仅支持 .xlsx 文件", status_code=400)
    path = _save_upload(file)
    engine = XlsxEngine({"file_path": path}, {})
    tables = engine.list_tables()
    sheets = []
    for t in tables:
        cols = engine.columns(t.name)
        sheets.append(
            {
                "name": t.name,
                "cols": [{"name": c.name, "type": c.source_type} for c in cols],
                "rows": int((t.comment or "0").replace(" 行", "") or 0),
            }
        )
    return {"sheets": sheets}


# —— 同步状态 / 重试 ——

def source_state_to_dict(state: registry.SyncJobState) -> dict:
    return {
        "job_id": state.job_id,
        "datasource_id": state.datasource_id,
        "engine": state.engine_type,
        "source": state.source,
        "target_database": state.target_database,
        "target_table": state.target_table,
        "status": state.status,
        "retry_count": state.retry_count,
        "max_retries": state.max_retries,
        "error_message": state.error_message,
        "rows_loaded": state.rows_loaded,
        "attempts": [
            {
                "attempt": a.attempt,
                "status": a.status,
                "rows_loaded": a.rows_loaded,
                "finished_at": a.finished_at,
                "error_message": a.error_message,
            }
            for a in state.attempts
        ],
        "started_at": state.started_at,
        "finished_at": state.finished_at,
    }


def get_sync_status(job_id: str) -> dict:
    state = registry.registry.get(job_id)
    if state is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"同步任务不存在（可能因服务重启丢失）: {job_id}", status_code=404)
    return source_state_to_dict(state)


def retry_sync(db: Session, job_id: str) -> dict:
    state = registry.registry.get(job_id)
    if state is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"同步任务不存在: {job_id}", status_code=404)
    if state.status in ("running", "pending"):
        raise ApiError(ErrorCode.VALIDATION, f"任务正在执行中，无法重试: {job_id}", status_code=400)
    ds = _row(db, state.datasource_id)
    engine = make_engine(ds.engine, ds.conn.conn_meta or {}, ds.conn.credentials or {})
    cfg = registry.SyncJobConfig(
        job_id=new_job_id(),
        datasource_id=state.datasource_id,
        engine_type=state.engine_type,
        source=state.source,
        target_database=state.target_database,
        target_table=state.target_table,
        max_retries=state.max_retries,
        truncate=True,
        engine=engine,
    )
    new_state = registry.registry.submit(cfg)
    return {"job_id": new_state.job_id, "status": new_state.status}


def list_jobs(datasource_id: str) -> list[dict]:
    states = registry.registry.list()
    jobs = [source_state_to_dict(s) for s in states if s.datasource_id == datasource_id]
    jobs.sort(key=lambda j: j.get("started_at") or "", reverse=True)
    return jobs