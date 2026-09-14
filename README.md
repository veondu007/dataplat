# DataPlat 企业级数仓平台

面向企业的一站式大数据开发与治理平台。能力规划参考阿里云 DataWorks。

| 项 | 约定 |
|----|------|
| 计算引擎 | Apache Doris |
| 查询身份 | Doris **个人账号**（与平台用户 1:1） |
| 问数模型 | **公有云** OpenAI 兼容 API |
| 当前版本 | 见 [`VERSION`](VERSION)（现为 `0.1.0-dev`） |

P0 三条线：数据资产、SQL 开发、AI 问数。

## 仓库结构

```text
DataPlat/
├── VERSION                  # 产品版本单一来源
├── CHANGELOG.md
├── apps/
│   ├── web/                 # React 控制台
│   └── api/                 # FastAPI（资产 / SQL Gateway / 问数）
│       ├── app/
│       │   ├── core/        # 配置 / 统一响应 / 异常 / request_id / 数据库
│       │   ├── models/      # SQLAlchemy 领域模型（workspaces/datasources/tables/columns）
│       │   └── modules/     # workspace / asset / sql / aiqa
│       ├── alembic/         # 数据库迁移
│       └── tests/
├── collectors/doris/        # Doris 元数据采集（独立包）
├── deploy/                  # Compose、环境变量模板
├── docs/                    # 规划 / 需求 / 架构 / 设计 / API / 运维
└── .github/workflows/ci.yml
```

## 文档

| 文档 | 内容 |
|------|------|
| [平台总体规划](docs/00-overview/平台总体规划.md) | 产品范围与分期 |
| [数据资产需求](docs/01-requirements/数据资产平台-需求说明书.md) | 数据地图 |
| [SQL 开发需求](docs/01-requirements/SQL开发平台-需求说明书.md) | 即席查询 |
| [AI 问数需求](docs/01-requirements/AI问数-需求说明书.md) | NL2SQL |
| [工程架构](docs/02-architecture/工程架构与技术选型.md) | 前后端选型 |
| [数据库模型](docs/03-design/数据库模型.md) | P0 表结构与 Alembic |
| [API 设计规范](docs/04-api/API设计规范.md) | 响应信封 / 错误码 / 端点 |
| [开发测试发版](docs/05-ops/环境与发版规范.md) | 环境、SemVer、CI |

## 本地启动

需要 Node 18+、Python 3.10、Docker。

```bash
docker compose -f deploy/docker-compose.yml up -d

cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000

cd apps/web
npm install
npm run dev
```

- 控制台：http://127.0.0.1:5173
- API 文档：http://127.0.0.1:8000/docs

## 版本与环境

`local` → `dev` → `test`（`*-rc.N`）→ `prod`（`vX.Y.Z`）。P0 首发目标 **0.1.0**。

- 产品版本单一来源：根目录 `VERSION`（后端启动 banner 与前端均自动读取）。
- 各 docs 文档头部「版本」为文档版本，与产品版本无关，详见 [开发测试发版](docs/05-ops/环境与发版规范.md)。
