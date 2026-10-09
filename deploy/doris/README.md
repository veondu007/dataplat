# DataPlat Doris 集群（本地 Docker）

本目录部署一个 **2 FE（1 master + 1 follower）+ 2 BE** 的 Apache Doris 集群，
内存 **每个实例 5G**，作为 DataPlat 的**业务数据源**（SQL 工作台 / AI 问数 / 采集目标）。

平台自身的元数据库仍为 PostgreSQL（`../docker-compose.yml` 根 Compose 的 `postgres`）。

## 1. 拓扑与端口

| 组件 | 容器 | 镜像 | 内存 | 对外端口 |
|------|------|------|------|----------|
| FE (master) | `dataplat-doris-fe-1` | `apache/doris:2.0.0_alpha-fe-x86_64` | 5G | 8030(Web UI) / 9030(mysql 协议) |
| FE (follower) | `dataplat-doris-fe-2` | 同上 | 5G | 8031 / 9031 |
| BE | `dataplat-doris-be-1` | `apache/doris:2.0.0_alpha-be-x86_64` | 5G | 8041(metrics) |
| BE | `dataplat-doris-be-2` | 同上 | 5G | 8042 |

内网固定 IP：FE=10.0.80.2/3，BE=10.0.80.4/5。FE 编辑日志端口 9010，BE 心跳 9050。

> 镜像使用 `docker.1panel.live/` 前缀（Docker Hub 拉不动时的国内加速镜像）。
> 若你的环境能直连 Docker Hub，可把 `image:` 改回 `apache/doris:2.0.0_alpha-*`。

## 2. 启动

```bash
cd deploy/doris
docker compose up -d
# 查看就绪
docker compose ps
# 等待 FE 选主 + BE 注册（首次约 1~3 分钟）
docker compose logs -f fe-1 | grep -i "ready" --color  # FE 就绪
mysql -h127.0.0.1 -P9030 -uroot -e "SHOW FRONTENDS; SHOW BACKENDS;"  # BE 应 Alive=true
```

Doris 2.0 `root` 默认**空密码**。生产请务必修改（见第 5 节）。

## 3. 初始化 SQL（信贷测试库）

首次启动时，BE 容器会自动执行 `./init-sql/*.sql`（镜像的 `/docker-entrypoint-initdb.d` 机制），
创建信贷领域测试库 `credit` 与演示数据：

| 表 | 类型 | 说明 |
|----|------|------|
| `credit.customer` | Unique Key | 客户维度（征信分、状态） |
| `credit.account` | Unique Key | 账户维度 |
| `credit.loan_contract` | Unique Key | 贷款合同事实（金额/余额/利率/逾期天数） |
| `credit.repay_record` | Unique Key | 还款流水事实 |
| `credit.overdue_record` | Unique Key | 逾期事实 |
| `credit.loan_summary_daily` | Aggregate | 按日产品汇总（贷款/逾期指标） |

验证：

```bash
mysql -h127.0.0.1 -P9030 -uroot -e "USE credit; SHOW TABLES; SELECT COUNT(*) FROM customer;"
```

## 4. 健康检查

| 检查项 | 命令 |
|--------|------|
| 集群状态 | `mysql -h127.0.0.1 -P9030 -uroot -e "SHOW FRONTENDS; SHOW BACKENDS;"` |
| FE Web UI | 浏览器打开 `http://127.0.0.1:8030`（默认账号 root / 空密码） |
| BE 指标 | `curl http://127.0.0.1:8041/metrics` |
| 服务日志 | `docker compose -f deploy/doris/docker-compose.yml logs -f fe-1` |

## 5. 注意事项

- **内存**：本集群合计约 20G（4 实例 × 5G）。Docker Desktop 需在 Settings → Resources → Memory 分配足够（建议 ≥ 16G，本机 48G 可直接给足）。若内存吃紧，可调小 `mem_limit`。
- **数据持久化**：`fe-*/doris-meta`、`be-*/storage` 挂载到本地目录，`docker compose down` 不丢数据；需要**重置集群**时删掉这些目录再 `up`。
- **重置集群**：
  ```bash
  cd deploy/doris && docker compose down -v
  rm -rf fe-* be-*        # 清空元数据与存储
  docker compose up -d    # 重新初始化（含信贷 SQL）
  ```
- **只跑一次初始化**：`/docker-entrypoint-initdb.d` 只在 `be/storage/data` 不存在时执行一次。
  需要重灌数据时，请重置 BE 目录或手动执行 `init-sql/001_credit.sql`。
- **账号安全**：Doris 2.0 root 默认空密码，仅限本地体验；上线前必须 `SET PASSWORD` 并建只读采集账号。

## 6. 与 DataPlat 的对接

| 用途 | 连接串 | 说明 |
|------|--------|------|
| SQL 工作台 / AI 问数 | `mysql://root@127.0.0.1:9030` | API 侧 `DATAPLAT_DORIS_*` 配置 |
| 元数据采集（只读） | 独立只读账号（见 `collectors/doris/README.md`） | 严禁使用 root 采集 |
| 平台元数据库 | `postgresql://dataplat:dataplat@127.0.0.1:5432/dataplat` | 根 Compose 的 postgres，保持不变 |
