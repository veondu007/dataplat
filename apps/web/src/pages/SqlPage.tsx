import { Button, Card, Input, Typography } from "antd";
import { useState } from "react";

export default function SqlPage() {
  const [sql, setSql] = useState("SELECT 1");
  const [result, setResult] = useState("");

  async function run() {
    const res = await fetch("/api/v1/sql/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql }),
    });
    const body = await res.json();
    setResult(JSON.stringify(body, null, 2));
  }

  return (
    <Card
      title="SQL 工作台"
      extra={
        <Button type="primary" onClick={run}>
          运行（只读校验）
        </Button>
      }
    >
      <Input.TextArea rows={10} value={sql} onChange={(e) => setSql(e.target.value)} />
      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
        执行走个人 Doris 账号。当前为护栏骨架，未绑定账号时不会连 FE。
      </Typography.Paragraph>
      <pre>{result}</pre>
    </Card>
  );
}
