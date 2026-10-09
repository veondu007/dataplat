import { Button, Modal, Space, Table, Tag, Tooltip, message } from "antd";
import { RedoOutlined } from "@ant-design/icons";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { Datasource, SyncJobStatus } from "./types";

type Props = {
  datasource: Datasource | null;
  onClose: () => void;
};

const STATUS_TAG: Record<string, { label: string; color: string }> = {
  pending: { label: "排队中", color: "default" },
  running: { label: "运行中", color: "processing" },
  success: { label: "成功", color: "success" },
  failed: { label: "失败", color: "error" },
};

export default function SyncJobsModal({ datasource, onClose }: Props) {
  const [jobs, setJobs] = useState<SyncJobStatus[]>([]);
  const [loading, setLoading] = useState(false);

  async function load() {
    if (!datasource) return;
    setLoading(true);
    try {
      const data = await api<SyncJobStatus[]>(`/datasources/sync/jobs?datasource_id=${datasource.id}`);
      setJobs(data);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载任务失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (datasource) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasource?.id]);

  async function rerun(jobId: string) {
    try {
      await api<{ job_id: string }>(`/datasources/sync/${jobId}/retry`, { method: "POST" });
      message.success("已触发重跑");
      load();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "重跑失败");
    }
  }

  return (
    <Modal
      title={`同步任务：${datasource?.name ?? ""}`}
      open={Boolean(datasource)}
      onCancel={onClose}
      footer={
        <Space>
          <Button onClick={load}>刷新</Button>
          <Button type="primary" onClick={onClose}>
            关闭
          </Button>
        </Space>
      }
      width={860}
      destroyOnClose
    >
      <Table<SyncJobStatus>
        rowKey="job_id"
        size="small"
        loading={loading}
        dataSource={jobs}
        pagination={{ pageSize: 10 }}
        locale={{ emptyText: "暂无同步任务" }}
        columns={[
          { title: "Job", dataIndex: "job_id", width: 180, ellipsis: true },
          {
            title: "状态",
            dataIndex: "status",
            width: 90,
            render: (v: string) => {
              const m = STATUS_TAG[v] ?? { label: v, color: "default" };
              return <Tag color={m.color}>{m.label}</Tag>;
            },
          },
          { title: "来源", dataIndex: "source", ellipsis: true },
          { title: "目标表", dataIndex: "target_table", ellipsis: true },
          {
            title: "重试",
            width: 90,
            render: (_, r) => `${r.retry_count}/${r.max_retries}`,
          },
          {
            title: "行数",
            dataIndex: "rows_loaded",
            width: 80,
            render: (v: number) => v?.toLocaleString() ?? "0",
          },
          {
            title: "错误",
            dataIndex: "error_message",
            ellipsis: true,
            render: (v: string | null | undefined) =>
              v ? (
                <Tooltip title={v}>
                  <Tag color="red" style={{ maxWidth: 200 }}>
                    {v.length > 24 ? `${v.slice(0, 24)}…` : v}
                  </Tag>
                </Tooltip>
              ) : (
                <span>-</span>
              ),
          },
          {
            title: "操作",
            width: 100,
            render: (_, r) =>
              r.status === "failed" ? (
                <Button type="link" size="small" icon={<RedoOutlined />} onClick={() => rerun(r.job_id)}>
                  重跑
                </Button>
              ) : null,
          },
        ]}
      />
    </Modal>
  );
}