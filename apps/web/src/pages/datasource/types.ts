export type EngineType = "mysql" | "maxcompute" | "xlsx";

export type Datasource = {
  id: string;
  workspace_id: string;
  name: string;
  engine: EngineType;
  created_at: string;
  conn_meta?: Record<string, unknown> | null;
  credentials?: Record<string, unknown> | null;
};

export type DatasourceCreatePayload = {
  name: string;
  engine: EngineType;
  workspace_id?: string;
  // mysql
  host?: string;
  port?: number;
  user?: string;
  password?: string;
  database?: string;
  // maxcompute
  endpoint?: string;
  project?: string;
  access_id?: string;
  access_key?: string;
  jar_path?: string;
};

export type SourceTable = {
  database_name: string;
  name: string;
  comment?: string | null;
};

export type SyncStartResponse = {
  job_id: string;
  status: string;
};

export type JobStatus = "pending" | "running" | "success" | "failed";

export type SyncAttempt = {
  attempt: number;
  status: string;
  rows_loaded: number;
  finished_at?: string | null;
  error_message?: string | null;
};

export type SyncJobStatus = {
  job_id: string;
  datasource_id: string;
  engine: EngineType;
  source: string;
  target_database: string;
  target_table: string;
  status: JobStatus;
  retry_count: number;
  max_retries: number;
  error_message?: string | null;
  rows_loaded: number;
  attempts: SyncAttempt[];
  started_at?: string | null;
  finished_at?: string | null;
};

export type XlsxSheet = {
  name: string;
  cols: { name: string; type: string }[];
  rows: number;
};

export type XlsxParseResult = {
  sheets: XlsxSheet[];
};

export const ENGINE_META: Record<EngineType, { label: string; color: string }> = {
  mysql: { label: "MySQL", color: "blue" },
  maxcompute: { label: "MaxCompute", color: "purple" },
  xlsx: { label: "XLSX", color: "green" },
};

export const DORIS_TYPES = [
  "BIGINT",
  "INT",
  "SMALLINT",
  "TINYINT",
  "DOUBLE",
  "FLOAT",
  "DECIMAL(20,2)",
  "BOOLEAN",
  "DATEV2",
  "DATETIME",
  "VARCHAR(255)",
  "VARCHAR(65533)",
  "CHAR(32)",
];