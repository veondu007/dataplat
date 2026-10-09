import { Alert, Form, Input, InputNumber, Modal, Select, message } from "antd";
import { useState } from "react";
import { api } from "../../lib/api";
import type { DatasourceCreatePayload, EngineType } from "./types";

type Props = {
  open: boolean;
  onCancel: () => void;
  onCreated: () => void;
};

export default function DatasourceFormModal({ open, onCancel, onCreated }: Props) {
  const [form] = Form.useForm<DatasourceCreatePayload>();
  const [engine, setEngine] = useState<EngineType>("mysql");
  const [loading, setLoading] = useState(false);

  function handleEngineChange(v: EngineType) {
    setEngine(v);
    // 切换引擎时保留 name/engine，重置其余连接字段
    const name = form.getFieldValue("name");
    form.resetFields();
    if (name) form.setFieldValue("name", name);
    form.setFieldValue("engine", v);
  }

  function handleCancel() {
    form.resetFields();
    setEngine("mysql");
    onCancel();
  }

  async function onFinish(values: DatasourceCreatePayload) {
    setLoading(true);
    try {
      await api<{ id: string }>("/datasources", {
        method: "POST",
        body: JSON.stringify(values),
      });
      message.success("数据源创建成功");
      handleCancel();
      onCreated();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "创建失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal
      title="新建数据源"
      open={open}
      onCancel={handleCancel}
      onOk={() => form.submit()}
      confirmLoading={loading}
      okText="创建"
      destroyOnClose
    >
      <Form form={form} layout="vertical" onFinish={onFinish} initialValues={{ engine: "mysql" }}>
        <Form.Item name="name" label="数据源名称" rules={[{ required: true, message: "请输入名称" }]}>
          <Input placeholder="例如：业务库 MySQL / 数仓 MaxCompute" />
        </Form.Item>
        <Form.Item name="engine" label="引擎类型" rules={[{ required: true }]}>
          <Select
            onChange={handleEngineChange}
            options={[
              { value: "mysql", label: "MySQL" },
              { value: "maxcompute", label: "MaxCompute" },
              { value: "xlsx", label: "XLSX（文件导入）" },
            ]}
          />
        </Form.Item>

        {engine === "mysql" && (
          <>
            <Form.Item name="host" label="Host" rules={[{ required: true, message: "请输入 Host" }]}>
              <Input placeholder="127.0.0.1" />
            </Form.Item>
            <Form.Item name="port" label="端口" initialValue={3306}>
              <InputNumber min={1} max={65535} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="database" label="数据库" rules={[{ required: true, message: "请输入库名" }]}>
              <Input placeholder="business_db" />
            </Form.Item>
            <Form.Item name="user" label="用户名" rules={[{ required: true, message: "请输入用户名" }]}>
              <Input placeholder="root" />
            </Form.Item>
            <Form.Item name="password" label="密码" rules={[{ required: true, message: "请输入密码" }]}>
              <Input.Password />
            </Form.Item>
          </>
        )}

        {engine === "maxcompute" && (
          <>
            <Form.Item name="endpoint" label="Endpoint" rules={[{ required: true, message: "请输入 Endpoint" }]}>
              <Input placeholder="service.cn-beijing.maxcompute.aliyun.com/api" />
            </Form.Item>
            <Form.Item name="project" label="项目空间" rules={[{ required: true, message: "请输入项目空间" }]}>
              <Input placeholder="my_project" />
            </Form.Item>
            <Form.Item name="access_id" label="AccessKey ID" rules={[{ required: true, message: "请输入 AccessKey ID" }]}>
              <Input placeholder="LTAI..." />
            </Form.Item>
            <Form.Item name="access_key" label="AccessKey Secret" rules={[{ required: true, message: "请输入 AccessKey Secret" }]}>
              <Input.Password />
            </Form.Item>
            <Form.Item name="jar_path" label="ODPS JDBC Jar 路径">
              <Input placeholder="C:\\odps\\odps-jdbc.jar（可选）" />
            </Form.Item>
          </>
        )}

        {engine === "xlsx" && (
          <Alert
            type="info"
            showIcon
            message="XLSX 数据源无需连接参数，文件在上传同步时提交"
            style={{ marginTop: 8 }}
          />
        )}
      </Form>
    </Modal>
  );
}