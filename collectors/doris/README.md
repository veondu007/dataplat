# DataPlat Doris collector

P0 uses a dedicated read-only Doris user for metadata collection.
Query / preview / AIQA must **never** use this account — those use the user's personal Doris identity (SQL Gateway).

## 独立包

本目录为独立 Python 包（`dataplat-collector-doris`，见 `pyproject.toml`），
后续由 `apps/api` 作为依赖引入（进程内 worker）或单独部署（独立 worker），
采集范围与模型对齐 `docs/03-design/数据库模型.md`。
