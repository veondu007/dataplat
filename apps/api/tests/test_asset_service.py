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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])