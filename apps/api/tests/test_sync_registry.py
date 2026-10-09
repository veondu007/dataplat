"""同步 registry 重试状态机单元测试（mock 引擎 + mock stream load，不碰真实 Doris）。"""

import pytest

from app.modules.datasource.sync import registry as reg
from app.modules.datasource.sync.engines.base import BaseEngine, EngineColumn


class _FlakyEngine(BaseEngine):
    """read_rows 抛错 fail_times 次后成功，用于测重试。"""

    def __init__(self, fail_times: int = 0, rows: list | None = None):
        self.fail_times = fail_times
        self.rows = rows or [[1, "a"], [2, "b"]]

    def test_conn(self):
        return {"ok": True, "latency_ms": 1, "message": "ok"}

    def list_tables(self):
        return []

    def columns(self, table):
        return [EngineColumn("id", "int"), EngineColumn("name", "varchar")]

    def read_rows(self, table, batch_size=1000):
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("source read failed")
        yield self.rows


@pytest.fixture
def patch_stream_load(monkeypatch):
    """把 stream_load 替换成记录调用的假实现。"""

    calls = []

    def fake_stream_load(db, table, csv_bytes, label, columns):
        calls.append({"db": db, "table": table, "label": label})
        from app.modules.datasource.sync.common import StreamLoadResult

        return StreamLoadResult(status="Success", loaded_rows=2, total_rows=2, message="ok", label=label)

    monkeypatch.setattr("app.modules.datasource.sync.registry.stream_load", fake_stream_load)
    # _prepare_target 会 real 连 Doris；这里把 doris_ddl/连接也 mock
    monkeypatch.setattr(
        "app.modules.datasource.sync.registry._prepare_target", lambda config, engine: None
    )
    return calls


def _run_config(engine, max_retries=2):
    cfg = reg.SyncJobConfig(
        job_id="job_test",
        datasource_id="ds_x",
        engine_type="mysql",
        source="t",
        target_database="credit",
        target_table="ods_t",
        max_retries=max_retries,
        truncate=True,
        engine=engine,
    )
    state = reg.SyncJobState(job_id="job_test", datasource_id="ds_x", engine_type="mysql", source="t", target_database="credit", target_table="ods_t", max_retries=max_retries)
    return cfg, state


def test_success_first_try(patch_stream_load):
    cfg, state = _run_config(_FlakyEngine(fail_times=0))
    reg._run(cfg, state)
    assert state.status == "success"
    assert state.attempts[-1].status == "success"
    assert state.retry_count == 0


def test_retries_then_success(patch_stream_load):
    # 前 1 次失败 → 自动重试成功
    cfg, state = _run_config(_FlakyEngine(fail_times=1), max_retries=2)
    reg._run(cfg, state)
    assert state.status == "success"
    assert len(state.attempts) == 2
    assert state.attempts[0].status == "failed"
    assert state.attempts[1].status == "success"


def test_retries_exhausted_fails(patch_stream_load):
    # 一直失败 → max_retries+1 次后 failed
    cfg, state = _run_config(_FlakyEngine(fail_times=999), max_retries=2)
    reg._run(cfg, state)
    assert state.status == "failed"
    assert len(state.attempts) == 3  # 1 次 + 2 次重试
    assert all(a.status == "failed" for a in state.attempts)
    assert state.retry_count == 2


def test_success_records_rows_loaded(patch_stream_load):
    cfg, state = _run_config(_FlakyEngine(fail_times=0))
    reg._run(cfg, state)
    assert state.rows_loaded == 2


def test_no_engine_fails_fast():
    cfg = reg.SyncJobConfig(
        job_id="j", datasource_id="d", engine_type="mysql", source="t",
        target_database="db", target_table="t", max_retries=2, truncate=True, engine=None,
    )
    state = reg.SyncJobState(job_id="j", datasource_id="d", engine_type="mysql", source="t", target_database="db", target_table="t", max_retries=2)
    reg._run(cfg, state)
    assert state.status == "failed"
    assert "引擎未初始化" in (state.error_message or "")