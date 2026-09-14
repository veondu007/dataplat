import { Button, Card, Input, Typography } from "antd";
import { useState } from "react";
import { api } from "../lib/api";

export default function AiqaPage() {
  const [question, setQuestion] = useState("昨天订单量是多少？");
  const [result, setResult] = useState("");

  async function ask() {
    try {
      const data = await api<{
        session_id: string;
        question: string;
        tables: unknown[];
        sql: string | null;
        needs_confirm: boolean;
        message: string;
      }>(`/aiqa/sessions/sess-demo/ask`, {
        method: "POST",
        body: JSON.stringify({ question }),
      });
      setResult(JSON.stringify(data, null, 2));
    } catch (err) {
      setResult(String(err instanceof Error ? err.message : err));
    }
  }

  return (
    <Card
      title="AI 问数"
      extra={
        <Button type="primary" onClick={ask}>
          提问
        </Button>
      }
    >
      <Input value={question} onChange={(e) => setQuestion(e.target.value)} />
      <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
        公有云模型 + 确认后执行。当前返回骨架响应，不调用模型、不跑 SQL。
      </Typography.Paragraph>
      <pre>{result}</pre>
    </Card>
  );
}
