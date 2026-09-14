# API 设计规范

- 文档版本：v0.1（独立于产品版本 `VERSION`）
- 日期：2026-09-14
- 状态：草案
- 运行时：`apps/api`（FastAPI），OpenAPI 文档见 `http://127.0.0.1:8000/docs`

## 1. 统一响应信封

所有 `/api/v1` 接口（成功与失败）返回统一结构：

```json
{
  "code": 0,
  "message": "ok",
  "data": {},
  "request_id": "2d2927c29da248a09d3f1e7ef96054eb"
}
```

- `code`：业务错误码，`0` 表示成功（见 §3）。
- `data`：业务数据；失败时通常为 `null`。
- `request_id`：单次请求唯一，同时写入响应头 `X-Request-Id`，用于日志与排障关联。

## 2. 错误码与 HTTP 映射

| code | HTTP | 含义 |
|------|------|------|
| 0 | 200 | 成功 |
| 40000 | 422 | 参数校验失败（Pydantic） |
| 40001 | 400 | SQL 护栏拦截（仅允许 SELECT/SHOW/EXPLAIN/DESC） |
| 40100 | 401 | 未认证（预留） |
| 40300 | 403 | 无权限（预留） |
| 40400 | 404 | 资源不存在（路由未匹配等） |
| 50000 | 500 | 服务端内部错误 |

错误响应示例：

```json
{
  "code": 40001,
  "message": "临时查询与问数仅允许 SELECT / SHOW / EXPLAIN / DESC",
  "data": null,
  "request_id": "25ae3f8e532e40998c6a798e384342df"
}
```

## 3. 鉴权（P0 约定，当前骨架未启用）

- 预留 JWT 方案：请求头 `Authorization: Bearer <token>`。
- 当前所有接口匿名可访问；接入时全局依赖注入，401/403 使用上表错误码。

## 4. 当前端点清单

统一前缀 `/api/v1`：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/workspaces` | 空间列表 |
| GET | `/workspaces/me/doris-binding` | 个人 Doris 账号绑定状态 |
| GET | `/assets/overview` | 资产规模总览 |
| GET | `/assets/search?q=` | 资产检索 |
| POST | `/sql/preview` | SQL 只读校验（未绑定账号不真实执行） |
| POST | `/aiqa/sessions` | 新建问数会话 |
| POST | `/aiqa/sessions/{session_id}/ask` | 问数提问（可携带待确认 SQL） |
| GET | `/health` | 健康检查（前缀外） |

## 5. 请求体模型（Pydantic）

| 模型 | 字段 | 约束 |
|------|------|------|
| `SqlPreviewRequest` | `sql` | 必填，1–50_000 字符 |
| `AiqaAskRequest` | `question` | 必填，1–2_000 字符 |
| | `sql` | 可选，≤ 50_000 字符，携带时过护栏 |

校验失败统一返回 `40000`（HTTP 422），`message` 为 `body.<字段>: <原因>` 拼接。

## 6. SQL 只读护栏

`/sql/preview` 与 `/aiqa/.../ask`（携带 `sql` 时）经过双层拦截（见 `apps/api/app/modules/sql/guard.py`）：

1. 去注释 / 去字符串后扫描写关键字（insert/update/delete/drop/alter/truncate/create/load/grant/revoke/merge/replace/rename/set）。
2. `sqlglot`（Doris 方言，失败回退 MySQL）AST 白名单：仅 `Select / Show / Describe`；`EXPLAIN` 内部语句必须同样只读；`SELECT ... FOR UPDATE` 带写锁，拒绝。

## 7. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v0.1 | 2026-09-14 | 初稿：信封 / 错误码 / 端点清单 / 护栏说明 |
