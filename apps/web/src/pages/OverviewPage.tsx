import { Card, Col, Row, Statistic } from "antd";
import { useEffect, useState } from "react";

type Overview = {
  datasource_count: number;
  table_count: number;
  column_count: number;
};

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null);

  useEffect(() => {
    fetch("/api/v1/assets/overview")
      .then((r) => r.json())
      .then((body) => setData(body.data))
      .catch(() => setData({ datasource_count: 0, table_count: 0, column_count: 0 }));
  }, []);

  return (
    <Row gutter={16}>
      <Col span={8}>
        <Card>
          <Statistic title="数据源" value={data?.datasource_count ?? "-"} />
        </Card>
      </Col>
      <Col span={8}>
        <Card>
          <Statistic title="表" value={data?.table_count ?? "-"} />
        </Card>
      </Col>
      <Col span={8}>
        <Card>
          <Statistic title="字段" value={data?.column_count ?? "-"} />
        </Card>
      </Col>
    </Row>
  );
}
