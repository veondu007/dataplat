export type ApiEnvelope<T> = {
  code: number;
  message: string;
  data: T;
  request_id: string;
};

const API_BASE = "/api/v1";

/** 统一请求后端：解信封，code !== 0 时抛错（message 展示给用户）。 */
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  let body: ApiEnvelope<T>;
  try {
    body = await res.json();
  } catch {
    throw new Error(`HTTP ${res.status}`);
  }
  if (!res.ok || body.code !== 0) {
    throw new Error(body.message || `请求失败 (${res.status})`);
  }
  return body.data;
}
