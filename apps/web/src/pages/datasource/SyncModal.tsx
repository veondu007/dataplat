import {
  Button, Form, Input, Modal, Select, Space, Spin, Statistic, Table, Tag,
  Typography, Upload, message,
} from "antd";
import { InboxOutlined } from "@ant-design/icons";
import { useEffect, useRef, useState } from "react";
import { api, apiUpload } from "../../lib/api";
import { usePolling } from "../../lib/usePolling";
import type { Datasource, SourceTable, SyncJobStatus, XlsxParseResult } from "./types";

const DEFAULT_TYPES = [
  { value: "BIGINT", label: "BIGINT" },
  { value: "INT", label: "INT" },
  { value: "SMALLINT", label: "SMALLINT" },
  { value: "DOUBLE", label: "DOUBLE" },
  { value: "DECIMAL(20,2)", label: "DECIMAL(20,2)" },
  { value: "BOOLEAN", label: "BOOLEAN" },
  { value: "DATEV2", label: "DATEV2" },
  { value: "DATETIME", label: "DATETIME" },
  { value: "VARCHAR(255)", label: "VARCHAR(255)" },
  { value: "VARCHAR(65533)", label: "VARCHAR(65533)" },
];

type Props = {
  datasource: Datasource | null;
  onClose: () => void;
};

export default function SyncModal({ datasource, onClose }: Props) {
  const isXlsx = datasource?.engine === "xlsx";

  const [tables, setTables] = useState<SourceTable[]>([]);
  const [loadingTables, setLoadingTables] = useState(false);

  const [fileList, setFileList] = useState<any[]>([]);
  const [sheets, setSheets] = useState<XlsxParseResult["sheets"]>([]);
  const [pickedSheet, setPickedSheet] = useState<string>();

  const [sourceTable, setSourceTable] = useState<string>();
  const [targetTable, setTargetTable] = useState<string>("");
  const [columnTypes, setColumnTypes] = useState<Record<string, string>>({});

  const [jobId, setJobId] = useState<string>();
  const [job, setJob] = useState<SyncJobStatus | null>(null);
  const [starting, setStarting] = useState(false);

  const jobRef = useRef<SyncJobStatus | null>(null);
  jobRef.current = job;
  const jobIdRef = useRef<string | undefined>(jobId);
  jobIdRef.current = jobId;

  // 打开时拉表（mysql/maxcompute）
  useEffect(() => {
    if (!datasource || isXlsx) return;
    setLoadingTables(true);
    api<SourceTable[]>(`/datasources/${datasource.id}/tables`)
      .then(setTables)
      .catch((e) => message.error(e.message))
      .finally(() => setLoadingTables(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasource?.id]);

  async function pickSheet(name: string) {
    setPickedSheet(name);
    const sheet = sheets.find((s) => s.name === name);
    if (sheet) setColumnTypes(Object.fromEntries(sheet.cols.map((c) => [c.name, c.type])));
  }

  // xlsx 上传后解析
  async function afterFile(file: File) {
    if (file.name && !file.name.toLowerCase().endsWith(".xlsx")) {
      message.error("仅支持 .xlsx 文件");
      return false;
    }
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await apiUpload<XlsxParseResult>(`/datasources/xlsx/parse`, fd);
      setSheets(res.sheets);
      if (res.sheets.length) {
        setPickedSheet(res.sheets[0].name);
        setColumnTypes(Object.fromEntries(res.sheets[0].cols.map((c) => [c.name, c.type])));
      }
      return false; // 阻止 antd 默认上传
    } catch (e) {
      message.error(e instanceof Error ? e.message : "解析失败");
      return false;
    }
  }

  // —— 启动同步 ——
  async function startSync() {
    if (!datasource) return;
    setStarting(true);
    setJob(null);
    try {
      let jobIdRes: string;
      if (isXlsx) {
        const file = fileList[0]?.originFileObj;
        if (!file) throw new Error("请选择 xlsx 文件");
        const fd = new FormData();
        fd.append("file", file);
        fd.append("sheet_name", pickedSheet ?? "");
        fd.append("target_table", targetTable || pickedSheet || "xlsx_import");
        if (Object.keys(columnTypes).length) fd.append("column_types", JSON.stringify(columnTypes));
        const data = await apiUpload<{ job_id: string }>(`/datasources/${datasource.id}/sync-xlsx`, fd);
        jobIdRes = data.job_id;
      } else {
        if (!sourceTable) throw new Error("请选择源表");
        const data = await api<{ job_id: string }>(`/datasources/${datasource.id}/sync`, {
          method: "POST",
          body: JSON.stringify({
            source_table: sourceTable,
            target_table: targetTable || sourceTable,
            max_retries: 2,
            truncate: true,
          }),
        });
        jobIdRes = data.job_id;
      }
      setJobId(jobIdRes);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "启动同步失败");
    } finally {
      setStarting(false);
    }
  }

  // —— 轮询 ——
  usePolling(
    Boolean(jobId) && !job?.status,
    2000,
    () => {
      const s = jobRef.current?.status;
      return s === "success" || s === "failed";
    },
    () => {
      const id = jobIdRef.current;
      if (!id) return;
      api<SyncJobStatus>(`/datasources/sync/${id}`)
        .then(setJob)
        .catch((e) => {
          message.error(e.message);
        });
    },
  );

  function close() {
    onClose();
    setJob(null);
    setJobId(undefined);
    setFileList([]);
    setSheets([]);
    setColumnTypes({});
    setSourceTable(undefined);
    setPickedSheet(undefined);
    setTargetTable("");
  }

  const running = job?.status === "running" || job?.status === "pending";
  const done = job && (job.status === "success" || job.status === "failed");

  const selectedSheet = sheets.find((s) => s.name === pickedSheet);
  const selectedCols = selectedSheet?.cols ?? [];

  return (
    <Modal
      title={`同步：${datasource?.name ?? ""}`}
      open={Boolean(datasource)}
      onCancel={close}
      footer={null}
      width={640}
      destroyOnClose
    >
      {!jobId && (
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          {isXlsx ? (
            <Upload.Dragger accept=".xlsx" maxCount={1} beforeUpload={afterFile} fileList={fileList} onChange={({ fileList: fl }) => setFileList(fl)}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽 .xlsx 文件到此处</p>
            </Upload.Dragger>
          ) : (
            <Form layout="vertical">
              <Form.Item label="源表">
                <Select
                  showSearch
                  loading={loadingTables}
                  placeholder="选择要同步的源表"
                  value={sourceTable}
                  onChange={setSourceTable}
                  options={tables.map((t) => ({ value: t.name, label: `${t.database_name}.${t.name}` }))}
                />
              </Form.Item>
            </Form>
          )}

          {isXlsx && sheets.length > 0 && (
            <Form layout="vertical">
              <Form.Item label="选择工作表">
                <Select
                  value={pickedSheet}
                  onChange={pickSheet}
                  options={sheets.map((s) => ({
                    value: s.name,
                    label: `${s.name}（${s.rows} 行）`,
                  }))}
                />
              </Form.Item>
            </Form>
          )}

          {isXlsx && sheets.length > 0 && (
            <>
              <Typography.Paragraph type="secondary" style={{ marginBottom: 4 }}>
                列类型（可修改，将映射到 Doris 目标表）：
              </Typography.Paragraph>
              <Table
                size="small"
                rowKey="name"
                pagination={false}
                dataSource={selectedCols}
                locale={{ emptyText: "请先选择工作表" }}
                columns={[
                  { title: "列名", dataIndex: "name" },
                  {
                    title: "源类型",
                    dataIndex: "type",
                    width: 120,
                  },
                  {
                    title: "Doris 类型",
                    dataIndex: "name",
                    render: (_v: string, rec: { name: string }) => (
                      <Select
                        size="small"
                        value={columnTypes[rec.name]}
                        onChange={(nv) => setColumnTypes((prev) => ({ ...prev, [rec.name]: nv }))}
                        options={DEFAULT_TYPES}
                        style={{ width: 180 }}
                      />
                    ),
                  },
                ]}
              />
            </>
          )}

          <Form layout="vertical">
            <Form.Item label="目标 Doris 表名">
              <Input
                placeholder={isXlsx ? "ods_xxxx（默认用工作表名）" : "保留原表名或输入新名"}
                value={targetTable}
                onChange={(e) => setTargetTable(e.target.value)}
              />
            </Form.Item>
          </Form>

          <Button type="primary" block loading={starting} onClick={startSync}>
            开始同步
          </Button>
        </Space>
      )}

      {jobId && (
        <div style={{ textAlign: "center", padding: "12px 0" }}>
          {running && <Spin size="large" />}
          <div style={{ margin: "12px 0" }}>
            {job?.status === "success" && <Tag color="success">同步成功</Tag>}
            {job?.status === "failed" && <Tag color="error">同步失败</Tag>}
            {running && <Tag color="processing">{job?.status === "pending" ? "排队中" : "运行中"}</Tag>}
          </div>
          <Space size="large">
            <Statistic title="已加载行" value={job?.rows_loaded ?? 0} />
            <Statistic title="重试/上限" value={`${job?.retry_count ?? 0}/${job?.max_retries ?? 2}`} />
          </Space>
          {job?.error_message && (
            <Typography.Paragraph style={{ marginTop: 12 }} type="danger">
              {job.error_message}
            </Typography.Paragraph>
          )}
          {job && job.attempts.length > 0 && (
            <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
              尝试：{job.attempts.map((a) => `第${a.attempt}次${a.status === "success" ? "成功" : "失败"}`).join(" · ")}
            </Typography.Paragraph>
          )}
          {done && (
            <Button style={{ marginTop: 12 }} onClick={close}>
              关闭
            </Button>
          )}
          {!done && (
            <Space style={{ marginTop: 12 }}>
              <Typography.Text type="secondary">正在同步，请稍候…</Typography.Text>
            </Space>
          )}
        </div>
      )}
    </Modal>
  );
}