# Changelog

本文件记录面向发布的变更。版本规则见 `docs/05-ops/环境与发版规范.md`。

## [0.1.0-dev] - 2026-09-14

### Added

- 产品需求：数据资产、SQL 开发、AI 问数（Doris 个人账号，公有云 LLM）
- 工程骨架：`apps/web`、`apps/api`、Compose、CI
- 发版约定：SemVer、环境（local/dev/test/prod）、Git 标签

### Changed

- SQL 护栏升级为 sqlglot AST + 关键字扫描双层拦截（仅 SELECT/SHOW/EXPLAIN/DESC，拒绝 FOR UPDATE 写锁）
- 统一响应信封补齐 `fail`/错误码/异常处理器；`request_id` 每请求一个并回写 `X-Request-Id`
- 请求体改为 Pydantic 模型校验（422 → code 40000）
- 产品版本单一来源：后端从根目录 `VERSION` 读取；前端 header 从 `package.json` 读取
- 新增数据库骨架：SQLAlchemy 2 + psycopg3 + Alembic（P0 四张核心表）
- CI 补 ruff lint；新增 `docs/03-design/数据库模型.md`、`docs/04-api/API设计规范.md`
- 前端新增统一 `api()` 封装，错误展示后端 message
