import {
  Card, Col, Empty, Row, Statistic, Spin, Table, Tag,
} from "antd";
import { DatabaseOutlined, FundOutlined, TableOutlined, ProfileOutlined } from "@ant-design/icons";
import type { EChartsOption } from "echarts";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Chart } from "../lib/charts";

type Stats = {
  totals: {
    datasource_count: number;
    database_count: number;
    table_count: number;
    column_count: number;
  };
  db_distribution: { database: string; count: number }[];
  engine_distribution: { engine: string; count: number }[];
  top_size: { name: string; database: string; data_size: number | null }[];
  top_rows: { name: string; database: string; num_rows: number | null }[];
  top_columns: { name: string; database: string; column_count: number }[];
};

const fmtBytes = (n?: number | null) => {
  if (n === null || n === undefined) return "-";
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)} GB`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)} MB`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)} KB`;
  return `${n} B`;
};

const fmtNum = (n?: number | null) => (n === null || n === undefined ? "-" : n.toLocaleString());

const BLUE = "#1677ff";

const dbBarOption = (rows: Stats["db_distribution"]): EChartsOption => ({
  tooltip: { trigger: "axis" },
  grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
  xAxis: { type: "category", data: rows.map((d) => d.database), axisLabel: { interval: 0, rotate: rows.length > 6 ? 30 : 0 } },
  yAxis: { type: "value", minInterval: 1 },
  series: [{ type: "bar", data: rows.map((d) => d.count), itemStyle: { color: BLUE }, barMaxWidth: 28 }],
});

const enginePieOption = (rows: Stats["engine_distribution"]): EChartsOption => ({
  tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
  legend: { bottom: 0 },
  series: [
    {
      type: "pie",
      radius: ["35%", "68%"],
      center: ["50%", "44%"],
      data: rows.map((e) => ({ name: e.engine, value: e.count })),
      label: { formatter: "{b} {c}" },
    },
  ],
});

const sizeBarOption = (rows: Stats["top_size"]): EChartsOption => ({
  tooltip: { trigger: "axis", formatter: (ps) => {
    const p = Array.isArray(ps) ? ps[0] : ps;
    return `${p.name}<br/>存储：${fmtBytes(p.value as number | null)}`;
  } },
  grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
  xAxis: { type: "value" },
  yAxis: { type: "category", data: rows.map((t) => t.name), axisLabel: { width: 90, overflow: "truncate" } },
  series: [{ type: "bar", data: rows.map((t) => t.data_size ?? 0), itemStyle: { color: "#13c2c2" }, barWidth: 14 }],
});

export default function AssetStatsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<Stats>("/assets/stats")
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div style={{ textAlign: "center", padding: 48 }}><Spin /></div>;
  }
  if (!stats) return <Empty description="暂无统计数据" />;

  const { totals, db_distribution, engine_distribution, top_size, top_rows, top_columns } = stats;

  const rankCols = (valueTitle: string | null) => [
    {
      title: "#",
      key: "rank",
      width: 44,
      render: (_: unknown, _r: unknown, i: number) => i + 1,
    },
    { title: "库.表", key: "name", render: (_: unknown, r: { name: string; database: string }) => <a>{`${r.database}.${r.name}`}</a> },
    ...(valueTitle ? [{ title: valueTitle, key: "v", width: 120, render: (_: unknown, r: { v?: number | null }) => fmtNum(r.v) }] : []),
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card size="small"><Statistic title="数据源" value={totals.datasource_count} prefix={<DatabaseOutlined />} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="数据库" value={totals.database_count} prefix={<FundOutlined />} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="表" value={totals.table_count} prefix={<TableOutlined />} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="字段" value={totals.column_count} prefix={<ProfileOutlined />} /></Card></Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card size="small" title="库分布（表数量 TOP12）">
            <Chart option={dbBarOption(db_distribution)} height={300} />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" title="表引擎分布">
            <Chart option={enginePieOption(engine_distribution)} height={300} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Card size="small" title="存储 TOP10">
            {top_size.length
              ? <Chart option={sizeBarOption(top_size)} height={300} />
              : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />}
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" title="行数 TOP10">
            <Table
              size="small"
              rowKey="name"
              pagination={false}
              dataSource={top_rows.map((t) => ({ ...t, v: t.num_rows }))}
              columns={rankCols("行数")}
              locale={{ emptyText: "暂无数据" }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" title="字段数 TOP10">
            <Table
              size="small"
              rowKey="name"
              pagination={false}
              dataSource={top_columns.map((t) => ({ ...t, v: t.column_count }))}
              columns={rankCols("字段数")}
              locale={{ emptyText: "暂无数据" }}
            />
          </Card>
        </Col>
      </Row>

      <div style={{ marginTop: 8 }}>
        <Tag>按库分布 / 引擎分布仅供参考：当前资产统一归属「Doris（内置）」数据源。</Tag>
      </div>
    </div>
  );
}