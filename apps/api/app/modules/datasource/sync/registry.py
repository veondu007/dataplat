"""进程内同步任务 registry + 后台执行线程（P0：内存态，Redis 未接入前的方案）。

限制（已文档化，见实现计划）：
- 内存态，服务重启后丢失所有任务状态；
- 单进程可用；
- 长任务占用工作线程。

终态：success / failed。运行中：pending / running。
状态对象经 ``get(job_id)`` 供 GET 轮询直接读取。
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.exceptions import ApiError
from app.modules.datasource.sync.common import (
    InferredColumn,
    doris_ddl,
    make_label,
    stream_load,
)
from app.modules.datasource.sync.engines.base import BaseEngine

logger = logging.getLogger(__name__)


@dataclass
class AttemptState:
    attempt: int
    status: str  # running / success / failed
    rows_loaded: int = 0
    finished_at: str | None = None
    error_message: str | None = None


@dataclass
class SyncJobState:
    job_id: str
    datasource_id: str
    engine_type: str
    source: str
    target_database: str
    target_table: str
    status: str = "pending"
    retry_count: int = 0
    max_retries: int = 2
    error_message: str | None = None
    attempts: list[AttemptState] = field(default_factory=list)
    started_at: str | None = None
    finished_at: str | None = None
    rows_loaded: int = 0


@dataclass
class SyncJobConfig:
    """一次性快照，供后台线程独立执行（不依赖请求上下文）。"""

    job_id: str
    datasource_id: str
    engine_type: str
    source: str  # 源表名 / sheet 名
    target_database: str
    target_table: str
    max_retries: int
    truncate: bool
    column_overrides: dict | None = None  # {column_name: doris_type}
    engine: BaseEngine | None = None
    # MySQL/MaxCompute：源列定义需经引擎解析，这里存引擎实例即可。
    # xlsx 的 inference 由引擎.columns() 提供，无需额外参数。


class _Registry:
    def __init__(self) -> None:
        self._jobs: dict[str, SyncJobState] = {}
        self._lock = threading.Lock()

    def submit(self, config: SyncJobConfig) -> SyncJobState:
        state = SyncJobState(
            job_id=config.job_id,
            datasource_id=config.datasource_id,
            engine_type=config.engine_type,
            source=config.source,
            target_database=config.target_database,
            target_table=config.target_table,
            max_retries=config.max_retries,
        )
        with self._lock:
            self._jobs[config.job_id] = state
        runner = threading.Thread(
            target=_run,
            args=(config, state),
            name=f"sync-{config.job_id[:8]}",
            daemon=True,
        )
        state.status = "running"
        state.started_at = _now()
        runner.start()
        return state

    def get(self, job_id: str) -> SyncJobState | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[SyncJobState]:
        with self._lock:
            return list(self._jobs.values())


registry = _Registry()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _apply_overrides(columns: list[InferredColumn], overrides: dict | None) -> list[InferredColumn]:
    """把用户指定的 {col: doris_type} 覆盖应用到推断列，保持列顺序。"""
    if not overrides:
        return columns
    out: list[InferredColumn] = []
    for c in columns:
        dtype = overrides.get(c.name, c.doris_type)
        out.append(InferredColumn(name=c.name, doris_type=dtype))
    return out


def _run(config: SyncJobConfig, state: SyncJobState) -> None:
    """后台执行循环（≤ max_retries+1 次），成功即停。"""
    engine = config.engine
    if engine is None:
        _finish_failed(state, "引擎未初始化")
        return

    for attempt in range(1, config.max_retries + 2):
        state.attempts.append(AttemptState(attempt=attempt, status="running"))
        last_error: str | None = None
        try:
            _prepare_target(config, engine)
            columns = _resolve_columns(config, engine)
            label = make_label(config.job_id, attempt)
            _stream(config, engine, columns, label, state, attempt)
            _finish_success(state, attempt)
            return
        except ApiError as exc:
            last_error = exc.message
        except Exception as exc:  # noqa: BLE001 - 后台线程捕获一切，落错误日志
            logger.exception("sync job %s failed (attempt %s)", config.job_id, attempt)
            last_error = str(exc)
        _record_failed_attempt(state, attempt, last_error)

    _finish_failed(state, state.error_message or "同步失败")


def _prepare_target(config: SyncJobConfig, engine: BaseEngine) -> None:
    """建 DDL（TRUNCATE 保留 schema）或建表。P0 简化：直接 CREATE + TRUNCATE。"""
    from app.modules.datasource.sync.doris import connect_doris_ddl

    columns = _resolve_columns(config, engine)
    conn = connect_doris_ddl()
    try:
        with conn.cursor() as cur:
            cur.execute(doris_ddl(config.target_database, config.target_table, columns))
            conn.commit()
            if config.truncate:
                cur.execute(
                    f"TRUNCATE TABLE `{config.target_database}`.`{config.target_table}`"
                )
                conn.commit()
    finally:
        conn.close()


def _resolve_columns(config: SyncJobConfig, engine: BaseEngine) -> list[InferredColumn]:
    from app.modules.datasource.sync.common import (
        maxcompute_to_doris,
        mysql_to_doris,
    )

    engine_cols = engine.columns(config.source)
    if config.engine_type == "mysql":
        cols = [InferredColumn(name=c.name, doris_type=mysql_to_doris(c.source_type)) for c in engine_cols]
    elif config.engine_type == "maxcompute":
        cols = [InferredColumn(name=c.name, doris_type=maxcompute_to_doris(c.source_type)) for c in engine_cols]
    else:  # xlsx：引擎已给出推断类型
        cols = [InferredColumn(name=c.name, doris_type=c.source_type) for c in engine_cols]
    return _apply_overrides(cols, config.column_overrides)


def _stream(config: SyncJobConfig, engine: BaseEngine, columns: list[InferredColumn], label: str, state: SyncJobState, attempt: int) -> None:
    from io import StringIO

    from app.modules.datasource.sync.common import csv_row

    assert engine is not None
    total_rows = 0
    # 拼接 CSV：先表头，再数据行（多次批 Stream Load，每批独立 label）
    for idx, batch in enumerate(engine.read_rows(config.source)):
        buf = StringIO()
        if idx == 0:
            _csv_write_header(buf, columns)
        for row in batch:
            buf.write(csv_row(_coerce_row(row, columns)))
            total_rows += 1
        batch_label = f"{label}_b{idx}" if idx else label
        stream_load(config.target_database, config.target_table, buf.getvalue().encode("utf-8"), batch_label, columns)
        # 周期性刷新进度
        state.rows_loaded = total_rows
    for a in state.attempts:
        if a.attempt == attempt:
            a.rows_loaded = total_rows
            break
    state.rows_loaded = total_rows


def _csv_write_header(io_handle, columns: list[InferredColumn]) -> None:
    from app.modules.datasource.sync.common import csv_row

    io_handle.write(csv_row([c.name for c in columns]))


def _coerce_row(row: list, columns: list[InferredColumn]) -> list:
    """按列数补齐/截断，空值置 None 以便 CSV 输出为空字符串。"""
    pad = len(columns)
    values = list(row)[:pad]
    while len(values) < pad:
        values.append(None)
    return values


def _record_failed_attempt(state: SyncJobState, attempt: int, error: str) -> None:
    for a in state.attempts:
        if a.attempt == attempt:
            a.status = "failed"
            a.error_message = error
            a.finished_at = _now()
            break
    state.error_message = error
    state.retry_count = attempt - 1


def _finish_success(state: SyncJobState, attempt: int) -> None:
    for a in state.attempts:
        if a.attempt == attempt and a.status == "running":
            a.status = "success"
            a.finished_at = _now()
            a.rows_loaded = state.rows_loaded
            break
    if not any(a.status == "success" for a in state.attempts):
        state.attempts.append(AttemptState(attempt=attempt, status="success", rows_loaded=state.rows_loaded, finished_at=_now()))
    state.status = "success"
    state.error_message = None
    state.finished_at = _now()


def _finish_failed(state: SyncJobState, error: str) -> None:
    state.status = "failed"
    state.error_message = error or state.error_message
    state.finished_at = _now()


def new_job_id() -> str:
    return uuid.uuid4().hex


def build_config(
    *,
    datasource_id: str,
    engine_type: str,
    source: str,
    target_database: str,
    target_table: str,
    max_retries: int,
    truncate: bool,
    engine: BaseEngine,
    column_overrides: dict | None = None,
) -> SyncJobConfig:
    return SyncJobConfig(
        job_id=new_job_id(),
        datasource_id=datasource_id,
        engine_type=engine_type,
        source=source,
        target_database=target_database,
        target_table=target_table,
        max_retries=max_retries,
        truncate=truncate,
        engine=engine,
        column_overrides=column_overrides,
    )