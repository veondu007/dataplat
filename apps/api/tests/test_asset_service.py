"""资产同步服务单元测试：时区转换 + 后台 job 状态机(mock connector,不依赖 DB/Doris)。"""

from zoneinfo import ZoneInfo

import pytest

from app.modules.asset import service
from app.modules.asset.service import AssetSyncService, now_cn


def test_now_cn_is_cn_timezone():
    """now_cn 必须带东八区 tz。"""
    dt = now_cn()
    assert dt.tzinfo is not None
    assert dt.utcoffset().total_seconds() == 8 * 3600


def test_now_cn_aware():
    assert now_cn().tzinfo == ZoneInfo("Asia/Shanghai")


class _FakeJobService(AssetSyncService):
    """替换 sync_all 为计数版,验证 run_async/get_status 状态机。"""

    def __init__(self):
        super().__init__()
        self.sync_calls = 0

    def sync_all(self):
        self.sync_calls += 1
        import time

        time.sleep(0.05)
        return {"databases": 1, "tables": 2, "columns": 3}


def test_async_job_transitions():
    import time

    svc = _FakeJobService()
    job_id = svc.run_async()
    # 立即轮询应为 running 或刚 success
    assert job_id
    # 等完成
    deadline = time.time() + 5
    status = None
    while time.time() < deadline:
        job = svc.get_status(job_id)
        if job and job.status == "success":
            status = job
            break
        time.sleep(0.02)
    assert status is not None, "job 未在超时内成功"
    assert status.status == "success"
    assert status.items == {"databases": 1, "tables": 2, "columns": 3}
    assert svc.sync_calls == 1


def test_get_status_unknown_job():
    svc = _FakeJobService()
    assert svc.get_status("nonexistent") is None


def test_job_to_dict_shape():
    j = service.AssetSyncJob(job_id="x", status="running", items={"a": 1})
    d = service.job_to_dict(j)
    assert d["job_id"] == "x"
    assert d["status"] == "running"
    assert d["items"] == {"a": 1}
    assert "started_at" in d and "finished_at" in d


# —— 资产查询 / 统计（内存 sqlite，不依赖 PG/Doris） ——


def _asset_session():
    """构造含 2 库 4 表 3 列的内存 sqlite 会话，供 get_stats / search_tables 单测。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.database import Base
    from app.models import Column, Datasource, Table

    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    s = Session(eng)
    s.add(Datasource(id="ds_doris", workspace_id="ws-default", name="Doris（内置）", engine="doris"))
    s.add_all(
        [
            Table(id="t1", datasource_id="ds_doris", database_name="credit", name="customer",
                  comment="客户", engine="UNIQUE", num_rows=6, data_size=2048),
            Table(id="t2", datasource_id="ds_doris", database_name="credit", name="loan_contract",
                  comment="贷款", engine="UNIQUE", num_rows=6, data_size=4096),
            Table(id="t3", datasource_id="ds_doris", database_name="dwd", name="agg_daily",
                  comment="汇总", engine="AGGREGATE", num_rows=1000, data_size=1000000),
            Table(id="t4", datasource_id="ds_doris", database_name="dwd", name="no_engine",
                  comment=None, engine=None, num_rows=None, data_size=None),
        ]
    )
    s.add_all(
        [
            Column(id="c1", table_id="t1", name="customer_id", data_type="bigint", position=1),
            Column(id="c2", table_id="t1", name="credit_score", data_type="int", position=2),
            Column(id="c3", table_id="t3", name="stat_date", data_type="datev2", position=1),
        ]
    )
    s.commit()
    return s


def test_get_stats_totals_and_distribution():
    s = _asset_session()
    st = service.get_stats(s)
    assert st["totals"]["table_count"] == 4
    assert st["totals"]["database_count"] == 2
    assert st["totals"]["column_count"] == 3
    assert st["totals"]["datasource_count"] == 1
    dbmap = {d["database"]: d["count"] for d in st["db_distribution"]}
    assert dbmap == {"credit": 2, "dwd": 2}
    engmap = {e["engine"]: e["count"] for e in st["engine_distribution"]}
    assert engmap == {"UNIQUE": 2, "AGGREGATE": 1, "未知": 1}


def test_get_stats_tops():
    s = _asset_session()
    st = service.get_stats(s)
    assert st["top_size"][0]["name"] == "agg_daily"  # data_size 最大
    assert st["top_size"][0]["database"] == "dwd"
    assert st["top_rows"][0]["name"] == "agg_daily"
    colsmap = {c["name"]: c["column_count"] for c in st["top_columns"]}
    assert colsmap["customer"] == 2  # 字段数 TOP 首位
    assert colsmap.get("agg_daily") == 1


def test_search_tables_by_table_name_and_column():
    s = _asset_session()
    # 表名命中(loan_contract 无同名列 → matched_field 为空)
    by_table = service.search_tables(s, "loan_contract")
    assert any(x["name"] == "loan_contract" for x in by_table)
    assert all(x["matched_field"] is None for x in by_table)
    # 字段命中(credit_score 列 → 返回所在表 customer 并标注列名)
    by_column = service.search_tables(s, "credit_score")
    assert any(
        x["name"] == "customer" and x["matched_field"] == "credit_score" for x in by_column
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])