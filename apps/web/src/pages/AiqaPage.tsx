import { Button, Card, Input, Typography } from "antd";
import { useState } from "react";

export default function AiqaPage() {
  const [question, setQuestion] = useState("昨天订单量是多少？");
  const [result, setResult] = useState("");

  async function ask() {
    const res = await fetch("/api/v1/aiqa/sessions/sess-demo/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const body = await res.json();
    setResult(JSON.stringify(body, null, 2));
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
