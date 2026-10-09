import { getToken, redirectToLogin } from "./auth";

export type ApiEnvelope<T> = {
  code: number;
  message: string;
  data: T;
  request_id: string;
};

const API_BASE = "/api/v1";

/** 解信封：401 跳登录；code !== 0 抛错（message 展示给用户）。 */
async function unwrap<T>(res: Response): Promise<T> {
  if (res.status === 401) {
    redirectToLogin();
    throw new Error("登录已过期，请重新登录");
  }
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

/** 统一请求后端：自动带 JWT、解信封，code !== 0 抛错（message 展示给用户）；401 跳登录。 */
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  return unwrap<T>(res);
}

/** multipart 上传：不设 JSON Content-Type（由浏览器自动带 boundary），仍带 Authorization。 */
export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  return unwrap<T>(res);
}
