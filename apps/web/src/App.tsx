import { DatabaseOutlined, MessageOutlined, CodeOutlined, HomeOutlined } from "@ant-design/icons";
import { Layout, Menu, Typography, Tag } from "antd";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import OverviewPage from "./pages/OverviewPage";
import AssetPage from "./pages/AssetPage";
import SqlPage from "./pages/SqlPage";
import AiqaPage from "./pages/AiqaPage";
import LoginPage from "./pages/LoginPage";
import { APP_VERSION } from "./lib/version";
import { isLoggedIn } from "./lib/auth";

const { Header, Sider, Content } = Layout;

export default function App() {
  const location = useLocation();

  // 登录页不渲染控制台布局
  if (location.pathname === "/login") {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    );
  }

  // 未登录：其余路由全部重定向到登录页
  if (!isLoggedIn()) {
    return <Navigate to="/login" replace />;
  }

  const selected = "/" + (location.pathname.split("/")[1] || "");

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider theme="light" width={220}>
        <div style={{ padding: 16, fontWeight: 700 }}>DataPlat</div>
        <Menu
          selectedKeys={[selected === "/" ? "/" : selected]}
          items={[
            { key: "/", icon: <HomeOutlined />, label: <Link to="/">总览</Link> },
            { key: "/assets", icon: <DatabaseOutlined />, label: <Link to="/assets">数据资产</Link> },
            { key: "/sql", icon: <CodeOutlined />, label: <Link to="/sql">SQL 开发</Link> },
            { key: "/aiqa", icon: <MessageOutlined />, label: <Link to="/aiqa">AI 问数</Link> },
          ]}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: "#fff",
            display: "flex",
            alignItems: "center",
            gap: 12,
            paddingInline: 24,
          }}
        >
          <Typography.Text>默认空间</Typography.Text>
          <Tag color="blue">Doris</Tag>
          <Tag>{APP_VERSION}</Tag>
        </Header>
        <Content style={{ margin: 24 }}>
          <Routes>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/assets" element={<AssetPage />} />
            <Route path="/sql" element={<SqlPage />} />
            <Route path="/aiqa" element={<AiqaPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}
