import { Button, Card, Popconfirm, Space, Table, Tag, Typography, message } from "antd";
import {
  ApiOutlined, CloudServerOutlined, DeleteOutlined, HistoryOutlined, PlusOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import DatasourceFormModal from "./datasource/DatasourceFormModal";
import SyncJobsModal from "./datasource/SyncJobsModal";
import SyncModal from "./datasource/SyncModal";
import { ENGINE_META } from "./datasource/types";
import type { Datasource, EngineType } from "./datasource/types";

export default function DatasourcePage() {
  const [data, setData] = useState<Datasource[]>([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [syncDs, setSyncDs] = useState<Datasource | null>(null);
  const [jobsDs, setJobsDs] = useState<Datasource | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api<Datasource[]>("/datasources"));
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载数据源失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function testConn(record: Datasource) {
    const hide = message.loading("测试连接中…", 0);
    try {
      const res = await api<{ ok: boolean; message: string; latency_ms: number }>(`/datasources/${record.id}/test`, {
        method: "POST",
      });
      hide();
      if (res.ok) {
        message.success(`${ENGINE_META[record.engine].label} 连接成功（${res.latency_ms ?? "-"}ms）：${res.message}`);
      } else {
        message.error(`${ENGINE_META[record.engine].label} 连接失败：${res.message}`);
      }
    } catch (e) {
      hide();
      message.error(e instanceof Error ? e.message : "测试连接失败");
    }
  }

  async function remove(record: Datasource) {
    try {
      await api(`/datasources/${record.id}`, { method: "DELETE" });
      message.success("已删除");
      load();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "删除失败");
    }
  }

  return (
    <Card
      title="数据源管理"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          新建数据源
        </Button>
      }
    >
      <Table<Datasource>
        rowKey="id"
        loading={loading}
        dataSource={data}
        locale={{ emptyText: "暂无数据源，点击右上角新建" }}
        pagination={{ pageSize: 10 }}
        columns={[
          {
            title: "名称",
            dataIndex: "name",
            render: (v: string) => (
              <Space>
                <CloudServerOutlined />
                {v}
              </Space>
            ),
          },
          {
            title: "引擎",
            dataIndex: "engine",
            width: 140,
            render: (v: EngineType) => {
              const m = ENGINE_META[v] ?? { label: v, color: "default" };
              return <Tag color={m.color}>{m.label}</Tag>;
            },
          },
          {
            title: "连接信息",
            dataIndex: "conn_meta",
            render: (v?: Record<string, unknown> | null) => {
              if (!v) return <Typography.Text type="secondary">-</Typography.Text>;
              const p: Record<string, unknown> = v as Record<string, unknown>;
              const host = p.host ?? p.endpoint ?? p.file_path;
              const db = p.database ?? p.project;
              return <Typography.Text type="secondary">{`${host ?? ""}${db ? ` / ${db}` : ""}`}</Typography.Text>;
            },
          },
          {
            title: "创建时间",
            dataIndex: "created_at",
            width: 180,
            render: (v: string) => (v ? new Date(v).toLocaleString() : "-"),
          },
          {
            title: "操作",
            width: 260,
            render: (_, record) => (
              <Space>
                <Button size="small" icon={<ApiOutlined />} onClick={() => testConn(record)}>
                  测试
                </Button>
                <Button size="small" icon={<SyncOutlined />} onClick={() => setSyncDs(record)}>
                  同步
                </Button>
                <Button size="small" icon={<HistoryOutlined />} onClick={() => setJobsDs(record)}>
                  任务
                </Button>
                <Popconfirm title="确定删除该数据源？" description="同步任务将一并删除" onConfirm={() => remove(record)}>
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </Space>
            ),
          },
        ]}
      />

      <DatasourceFormModal open={createOpen} onCancel={() => setCreateOpen(false)} onCreated={load} />
      <SyncModal datasource={syncDs} onClose={() => setSyncDs(null)} />
      <SyncJobsModal datasource={jobsDs} onClose={() => setJobsDs(null)} />
    </Card>
  );
}