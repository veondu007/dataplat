import { Button, Card, Input, Table, Tag, Typography } from "antd";
import { useState } from "react";
import { api } from "../lib/api";

type Column = { [key: string]: unknown };

type PreviewData = {
  accepted: boolean;
  sql: string;
  message: string;
  result: { columns: string[]; rows: Column[]; row_count: number; truncated: boolean };
};

export default function SqlPage() {
  const [sql, setSql] = useState("SELECT * FROM credit.customer LIMIT 10");
  const [result, setResult] = useState<PreviewData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await api<PreviewData>("/sql/preview", {
        method: "POST",
        body: JSON.stringify({ sql }),
      });
      setResult(data);
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card
      title="SQL 工作台"
      extra={
        <Button type="primary" onClick={run} loading={loading}>
          运行（只读）
        </Button>
      }
    >
      <Input.TextArea rows={10} value={sql} onChange={(e) => setSql(e.target.value)} />
      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
        在 Doris 执行只读 SQL（SELECT / SHOW / EXPLAIN / DESC）。目标库：credit（信贷测试库）。
      </Typography.Paragraph>
      {error && (
        <Typography.Paragraph type="danger" style={{ marginTop: 8 }}>
          {error}
        </Typography.Paragraph>
      )}
      {result && (
        <>
          <Tag color="green" style={{ marginBottom: 8 }}>
            {result.message} · {result.result.row_count} 行
            {result.result.truncated ? "（已截断）" : ""}
          </Tag>
          <Table<Column>
            rowKey={(r) => JSON.stringify(r)}
            size="small"
            dataSource={result.result.rows}
            columns={(result.result.columns ?? []).map((c) => ({
              title: c,
              dataIndex: c,
              ellipsis: true,
            }))}
            pagination={{ pageSize: 10 }}
            scroll={{ x: true }}
          />
          <Typography.Paragraph
            type="secondary"
            style={{ marginTop: 8 }}
            copyable={{ text: JSON.stringify(result, null, 2) }}
          >
            <pre style={{ maxHeight: 200, overflow: "auto" }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </Typography.Paragraph>
        </>
      )}
    </Card>
  );
}
