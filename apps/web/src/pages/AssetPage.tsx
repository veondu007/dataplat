import {
  AutoComplete, Button, Card, Col, Collapse, Descriptions, Drawer, Empty, Input, List, Row, Select, Space, Spin, Statistic, Table, Tag,
  Typography, message,
} from "antd";
import { DatabaseOutlined, SearchOutlined, SyncOutlined, TableOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { usePolling } from "../lib/usePolling";

type Overview = {
  datasource_count: number;
  database_count: number;
  table_count: number;
  column_count: number;
  collector_healthy: boolean;
};

type TableMeta = {
  id: string;
  database_name: string;
  name: string;
  comment?: string | null;
  num_rows?: number | null;
  data_size?: number | null;
  engine?: string | null;
  partition_cols?: string | null;
  last_synced_at?: string | null;
};

type ColumnMeta = {
  name: string;
  data_type: string;
  position: number;
  is_partition: boolean;
  comment?: string | null;
};

type TableDetail = TableMeta & {
  columns: ColumnMeta[];
  create_sql?: string | null;
};

/** 血缘边(手动登记)。 */
type LineageEdge = {
  lineage_id: string;
  table_id: string;
  database_name: string;
  name: string;
  edge_type: string;
};

/** 搜索命中项：TableMeta 基础上补充来源数据源与命中字段。 */
type SearchResult = TableMeta & {
  datasource_name?: string | null;
  matched_field?: string | null;
};

type SyncJobStatus = {
  job_id: string;
  status: string;
  items?: { databases?: number; tables?: number; columns?: number };
  error_message?: string | null;
};

const fmtBytes = (n?: number | null) => {
  if (n === null || n === undefined) return "-";
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)} GB`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)} MB`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)} KB`;
  return `${n} B`;
};

const fmtNum = (n?: number | null) => (n === null || n === undefined ? "-" : n.toLocaleString());

export default function AssetPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [databases, setDatabases] = useState<string[]>([]);
  const [selectedDb, setSelectedDb] = useState<string>();
  const [tables, setTables] = useState<TableMeta[]>([]);
  const [loadingTables, setLoadingTables] = useState(false);

  const [detail, setDetail] = useState<TableDetail | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  // 详情扩展：标签 / 血缘
  const [detailTags, setDetailTags] = useState<string[]>([]);
  const [allTags, setAllTags] = useState<{ id: string; name: string }[]>([]);
  const [detailLineage, setDetailLineage] = useState<{ upstream: LineageEdge[]; downstream: LineageEdge[] } | null>(null);
  const [tagInput, setTagInput] = useState<string[]>([]);
  const [lnSearch, setLnSearch] = useState("");
  const [lnOptions, setLnOptions] = useState<{ value: string; id: string }[]>([]);
  const [lnDir, setLnDir] = useState<"upstream" | "downstream">("upstream");
  const [lnRelatedId, setLnRelatedId] = useState("");

  function loadExtras(tableId: string) {
    api<string[]>(`/assets/tables/${tableId}/tags`).then(setDetailTags).catch(() => {});
    api<{ upstream: LineageEdge[]; downstream: LineageEdge[] }>(`/assets/tables/${tableId}/lineage`).then(setDetailLineage).catch(() => {});
  }

  function openDetail(row: TableMeta) {
    setDetailOpen(true);
    setDetailLoading(true);
    setDetailTags([]);
    setDetailLineage(null);
    api<TableDetail>(`/assets/tables/${row.id}`)
      .then((d) => {
        setDetail(d);
        loadExtras(row.id);
      })
      .catch((e) => message.error(e.message))
      .finally(() => setDetailLoading(false));
    if (!allTags.length) {
      api<{ id: string; name: string }[]>("/assets/tags").then(setAllTags).catch(() => {});
    }
  }

  async function addTag(tag: string) {
    if (!detail) return;
    const t = tag.trim();
    if (!t) return;
    try {
      await api(`/assets/tables/${detail.id}/tags`, { method: "POST", body: JSON.stringify({ tag: t }) });
      setDetailTags(await api<string[]>(`/assets/tables/${detail.id}/tags`));
      setTagInput([]);
    } catch (e) { message.error(e instanceof Error ? e.message : "打标失败"); }
  }

  async function removeTag(tag: string) {
    if (!detail) return;
    try {
      await api(`/assets/tables/${detail.id}/tags/${encodeURIComponent(tag)}`, { method: "DELETE" });
      setDetailTags((ts) => ts.filter((x) => x !== tag));
    } catch (e) { message.error(e instanceof Error ? e.message : "移除标签失败"); }
  }

  async function removeLineage(id: string) {
    if (!detail) return;
    try {
      await api(`/assets/tables/${detail.id}/lineage/${id}`, { method: "DELETE" });
      loadExtras(detail.id);
    } catch (e) { message.error(e instanceof Error ? e.message : "移除血缘失败"); }
  }

  async function searchLn(kw: string) {
    setLnSearch(kw);
    if (!kw.trim()) { setLnOptions([]); return; }
    try {
      const rows = await api<TableMeta[]>(`/assets/search?q=${encodeURIComponent(kw)}`);
      setLnOptions(rows.map((r) => ({ value: `${r.database_name}.${r.name}`, id: r.id })));
    } catch { setLnOptions([]); }
  }

  async function submitLineage() {
    if (!detail || !lnRelatedId) { message.warning("请先选择关联表"); return; }
    try {
      await api(`/assets/tables/${detail.id}/lineage`, {
        method: "POST",
        body: JSON.stringify({ related_table_id: lnRelatedId, direction: lnDir, edge_type: "manual" }),
      });
      setLnRelatedId("");
      setLnSearch("");
      loadExtras(detail.id);
    } catch (e) { message.error(e instanceof Error ? e.message : "登记血缘失败"); }
  }

  const [syncing, setSyncing] = useState(false);
  const [job, setJob] = useState<SyncJobStatus | null>(null);
  const [jobId, setJobId] = useState<string | undefined>(undefined);

  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);

  function doSearch(q: string) {
    const kw = q.trim();
    setSearchQ(kw);
    if (!kw) {
      setSearchResults(null);
      return;
    }
    setSearching(true);
    api<SearchResult[]>(`/assets/search?q=${encodeURIComponent(kw)}`)
      .then((rows) => setSearchResults(rows))
      .catch((e) => message.error(e.message))
      .finally(() => setSearching(false));
  }

  const loadOverview = () => api<Overview>("/assets/overview").then(setOverview).catch(() => {});
  const loadDatabases = () =>
    api<string[]>("/assets/databases").then((dbs) => {
      setDatabases(dbs);
      if (dbs.length && !selectedDb) setSelectedDb(dbs[0]);
    }).catch(() => {});

  useEffect(() => {
    loadOverview();
    loadDatabases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedDb) return;
    setLoadingTables(true);
    api<TableMeta[]>(`/assets/databases/${selectedDb}/tables`)
      .then(setTables)
      .catch((e) => message.error(e.message))
      .finally(() => setLoadingTables(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDb]);

  async function triggerSync() {
    setSyncing(true);
    setJob(null);
    setJobId(undefined);
    try {
      const d = await api<{ job_id: string }>("/assets/sync", { method: "POST" });
      setJobId(d.job_id);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "触发同步失败");
    } finally {
      setSyncing(false);
    }
  }

  usePolling(
    Boolean(jobId),
    2000,
    () => job?.status === "success" || job?.status === "failed",
    () => {
      if (!jobId) return;
      api<SyncJobStatus>(`/assets/sync/${jobId}`)
        .then((j) => {
          setJob(j);
          if (j.status === "success" || j.status === "failed") {
            loadOverview();
            loadDatabases();
          }
        })
        .catch(() => {});
    },
  );

  const running = job?.status === "running" || job?.status === "pending";

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="数据源" value={overview?.datasource_count ?? "-"} prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="数据库" value={overview?.database_count ?? "-"} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="表" value={overview?.table_count ?? "-"} prefix={<TableOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="字段" value={overview?.column_count ?? "-"} />
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <span>
            数据地图 <Tag style={{ marginLeft: 8 }} color="blue">Doris</Tag>
          </span>
        }
        extra={
          <Space wrap>
            <Input.Search
              placeholder="搜索表名 / 库名 / 字段"
              allowClear
              enterButton={<SearchOutlined />}
              style={{ width: 280 }}
              onSearch={doSearch}
            />
            <Button
              icon={<SyncOutlined spin={running} />}
              onClick={triggerSync}
              loading={syncing}
            >
              同步元数据{running ? "中…" : ""}
            </Button>
          </Space>
        }
      >
        {job?.status === "success" && job.items && (
          <Tag color="success" style={{ marginBottom: 12 }}>
            同步完成：{job.items.databases} 库 / {job.items.tables} 表 / {job.items.columns} 字段
          </Tag>
        )}
        {job?.status === "failed" && (
          <Tag color="error" style={{ marginBottom: 12 }}>{job.error_message}</Tag>
        )}

        {searchQ ? (
          <>
            <Tag color="blue" style={{ marginBottom: 12 }}>
              搜索 “{searchQ}”{searching ? " 中…" : `：${searchResults?.length ?? 0} 个结果`}
            </Tag>
            {searching ? (
              <div style={{ textAlign: "center", padding: 32 }}><Spin /></div>
            ) : !searchResults?.length ? (
              <Empty description="未找到匹配的表" />
            ) : (
              <Table<SearchResult>
                rowKey="id"
                size="small"
                dataSource={searchResults}
                pagination={{ pageSize: 10 }}
                columns={[
                  { title: "库.表", key: "fq", render: (_, r) => <a onClick={() => openDetail(r)}>{r.database_name}.{r.name}</a> },
                  { title: "命中字段", dataIndex: "matched_field", width: 140, render: (v) => (v ? <Tag color="gold">字段：{v}</Tag> : <Tag>表</Tag>) },
                  { title: "注释", dataIndex: "comment", ellipsis: true, render: (v) => v || "-" },
                  { title: "模型", dataIndex: "engine", width: 90, render: (v) => v || "-" },
                  { title: "行数", dataIndex: "num_rows", width: 90, render: fmtNum },
                  { title: "存储", dataIndex: "data_size", width: 100, render: fmtBytes },
                ]}
              />
            )}
          </>
        ) : (
        <Collapse
          activeKey={selectedDb}
          onChange={(k) => setSelectedDb(Array.isArray(k) ? (k[0] as string) : (k as string))}
          items={databases.map((db) => ({
            key: db,
            label: (
              <span>
                <DatabaseOutlined /> {db} <Tag>{tables.length} 表</Tag>
              </span>
            ),
            children: (
              <Table<TableMeta>
                rowKey="id"
                size="small"
                loading={loadingTables}
                dataSource={tables}
                pagination={{ pageSize: 8 }}
                columns={[
                  { title: "表名", dataIndex: "name", render: (v, r) => <a onClick={() => openDetail(r)}>{v}</a> },
                  { title: "注释", dataIndex: "comment", ellipsis: true, render: (v) => v || "-" },
                  { title: "模型", dataIndex: "engine", width: 90, render: (v) => v || "-" },
                  { title: "行数", dataIndex: "num_rows", width: 90, render: fmtNum },
                  { title: "存储", dataIndex: "data_size", width: 100, render: fmtBytes },
                  {
                    title: "同步时间",
                    dataIndex: "last_synced_at",
                    width: 160,
                    render: (v) => (v ? new Date(v).toLocaleString() : "-"),
                  },
                ]}
              />
            ),
          }))}
        />
        )}
      </Card>

      <Drawer
        title="表详情"
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width={720}
      >
        {detailLoading || !detail ? (
          <Typography.Text type="secondary">加载中…</Typography.Text>
        ) : (
          <>
            <Descriptions size="small" column={2} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="全限定名">{`${detail.database_name}.${detail.name}`}</Descriptions.Item>
              <Descriptions.Item label="表模型">{detail.engine || "-"}</Descriptions.Item>
              <Descriptions.Item label="行数">{fmtNum(detail.num_rows)}</Descriptions.Item>
              <Descriptions.Item label="存储">{fmtBytes(detail.data_size)}</Descriptions.Item>
              <Descriptions.Item label="注释" span={2}>{detail.comment || "-"}</Descriptions.Item>
              <Descriptions.Item label="分区键">{detail.partition_cols || "-"}</Descriptions.Item>
              <Descriptions.Item label="最近同步">{detail.last_synced_at ? new Date(detail.last_synced_at).toLocaleString() : "-"}</Descriptions.Item>
            </Descriptions>
            <Typography.Title level={5}>字段（{detail.columns.length}）</Typography.Title>
            <Table<ColumnMeta>
              rowKey="name"
              size="small"
              dataSource={detail.columns}
              pagination={false}
              columns={[
                { title: "字段", dataIndex: "name", render: (v, r) => (r.is_partition ? <Tag color="gold">{v}</Tag> : v) },
                { title: "类型", dataIndex: "data_type" },
                { title: "注释", dataIndex: "comment", ellipsis: true, render: (v) => v || "-" },
                { title: "分区键?", dataIndex: "is_partition", width: 90, render: (v) => (v ? <Tag color="gold">是</Tag> : <Tag>否</Tag>) },
              ]}
            />

            <Card size="small" title="建表语句" style={{ marginTop: 16 }}>
              {detail.create_sql ? (
                <Typography.Paragraph code copyable style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-all", fontSize: 12 }}>
                  {detail.create_sql}
                </Typography.Paragraph>
              ) : (
                <Typography.Text type="secondary">暂无建表语句（可重新同步元数据获取）</Typography.Text>
              )}
            </Card>

            <Card size="small" title="业务标签" style={{ marginTop: 16 }}>
              <Space wrap>
                {detailTags.length ? (
                  detailTags.map((t) => (
                    <Tag key={t} color="blue" closable onClose={() => removeTag(t)}>{t}</Tag>
                  ))
                ) : (
                  <Typography.Text type="secondary">暂无标签</Typography.Text>
                )}
                <Select
                  mode="tags"
                  style={{ minWidth: 180 }}
                  placeholder="输入或选择标签"
                  value={tagInput}
                  onChange={(v) => setTagInput(v)}
                  options={allTags.map((t) => ({ value: t.name, label: t.name }))}
                />
                <Button size="small" onClick={async () => { const list = [...tagInput]; for (const t of list) await addTag(t); }}>添加</Button>
              </Space>
            </Card>

            <Card size="small" title="血缘" style={{ marginTop: 16 }}>
              {!detailLineage ? (
                <Typography.Text type="secondary">加载中…</Typography.Text>
              ) : (
                <Row gutter={16}>
                  <Col span={12}>
                    <Typography.Text strong>上游</Typography.Text>
                    {detailLineage.upstream.length ? (
                      <List size="small" dataSource={detailLineage.upstream} renderItem={(e) => (
                        <List.Item actions={[<a key="rm" onClick={() => removeLineage(e.lineage_id)}>移除</a>]}>
                          <span>{e.database_name}.{e.name} <Tag color="green">{e.edge_type}</Tag></span>
                        </List.Item>
                      )} />
                    ) : <Typography.Text type="secondary">暂无上游</Typography.Text>}
                  </Col>
                  <Col span={12}>
                    <Typography.Text strong>下游</Typography.Text>
                    {detailLineage.downstream.length ? (
                      <List size="small" dataSource={detailLineage.downstream} renderItem={(e) => (
                        <List.Item actions={[<a key="rm" onClick={() => removeLineage(e.lineage_id)}>移除</a>]}>
                          <span>{e.database_name}.{e.name} <Tag color="orange">{e.edge_type}</Tag></span>
                        </List.Item>
                      )} />
                    ) : <Typography.Text type="secondary">暂无下游</Typography.Text>}
                  </Col>
                </Row>
              )}
              <div style={{ marginTop: 12 }}>
                <Space wrap>
                  <AutoComplete
                    style={{ width: 220 }}
                    value={lnSearch}
                    placeholder="搜索关联表"
                    options={lnOptions.map((o) => ({ value: o.value }))}
                    onChange={(v) => searchLn(v)}
                    onSelect={(v) => setLnRelatedId(lnOptions.find((o) => o.value === v)?.id ?? "")}
                    filterOption={false}
                  />
                  <Select value={lnDir} onChange={(v) => setLnDir(v)} style={{ width: 110 }}
                    options={[{ value: "upstream", label: "上游" }, { value: "downstream", label: "下游" }]} />
                  <Button size="small" type="primary" onClick={submitLineage}>登记血缘</Button>
                </Space>
                <div style={{ marginTop: 8 }}>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    血缘当前为手动登记；真实 SQL 作业解析后续接入（P1）。
                  </Typography.Text>
                </div>
              </div>
            </Card>
          </>
        )}
      </Drawer>
    </div>
  );
}
