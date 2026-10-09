"""P0 领域模型：工作空间 / 数据源 / 表 / 字段 + 数据源连接与同步任务。

对应 `docs/01-requirements/数据资产平台-需求说明书.md` §5 领域模型（逻辑）的落地子集。
Database / Partition / 血缘等实体随采集器迭代补充。
"""

from app.models.column import Column
from app.models.datasource import Datasource
from app.models.datasource_conn import DatasourceConn
from app.models.sync_job import SyncJob
from app.models.sync_run import SyncRun
from app.models.table import Table
from app.models.workspace import Workspace

__all__ = [
    "Workspace",
    "Datasource",
    "DatasourceConn",
    "Table",
    "Column",
    "SyncJob",
    "SyncRun",
]