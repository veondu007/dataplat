import { Card, Input, Table, Typography } from "antd";
import { useState } from "react";

export default function AssetPage() {
  const [keyword, setKeyword] = useState("");
  return (
    <Card title="数据资产">
      <Input.Search
        placeholder="搜索表名、字段、中文注释"
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        style={{ maxWidth: 480, marginBottom: 16 }}
      />
      <Typography.Paragraph type="secondary">
        骨架页。接入 Doris 采集器后在此展示检索结果。
      </Typography.Paragraph>
      <Table
        rowKey="id"
        dataSource={[]}
        columns={[
          { title: "表", dataIndex: "name" },
          { title: "库", dataIndex: "database" },
          { title: "Owner", dataIndex: "owner" },
        ]}
      />
    </Card>
  );
}
