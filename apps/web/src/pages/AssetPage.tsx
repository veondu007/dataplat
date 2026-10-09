import {
  Button, Card, Col, Collapse, Descriptions, Drawer, Row, Statistic, Table, Tag,
  Typography, message,
} from "antd";
import { DatabaseOutlined, SyncOutlined, TableOutlined } from "@ant-design/icons";
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

type TableDetail = TableMeta & { columns: ColumnMeta[] };

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

  const [syncing, setSyncing] = useState(false);
  const [job, setJob] = useState<SyncJobStatus | null>(null);
  const [jobId, setJobId] = useState<string | undefined>(undefined);

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

  function openDetail(row: TableMeta) {
    setDetailOpen(true);
    setDetailLoading(true);
    api<TableDetail>(`/assets/tables/${row.id}`)
      .then(setDetail)
      .catch((e) => message.error(e.message))
      .finally(() => setDetailLoading(false));
  }

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
          <Button
            icon={<SyncOutlined spin={running} />}
            onClick={triggerSync}
            loading={syncing}
          >
            同步元数据{running ? "中…" : ""}
          </Button>
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
          </>
        )}
      </Drawer>
    </div>
  );
}
