export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "olivesoft_token";

export const getToken = () => (typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY));

export const setToken = (token) => {
  if (typeof window === "undefined") return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
};

async function readError(res) {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) return data.detail.map((d) => d.msg).join(", ");
  } catch (e) {
    /* corps non JSON */
  }
  return `Erreur ${res.status}`;
}

function buildRequest(method, body, form) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (form) {
    payload = form;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  return { method, headers, body: payload };
}

async function request(path, options) {
  try {
    return await fetch(`${API_URL}${path}`, options);
  } catch (e) {
    throw new Error("Serveur injoignable. Vérifiez que l'API FastAPI est démarrée.");
  }
}

function handleUnauthorized(res, path) {
  if (res.status === 401 && !path.startsWith("/auth/")) {
    setToken(null);
    if (typeof window !== "undefined") window.location.href = "/login";
  }
}

export async function api(path, { method = "GET", body, form } = {}) {
  const res = await request(path, buildRequest(method, body, form));
  handleUnauthorized(res, path);
  if (!res.ok) throw new Error(await readError(res));
  return res.status === 204 ? null : res.json();
}

export async function apiDownload(path, fallbackName) {
  const res = await request(path, buildRequest("POST"));
  handleUnauthorized(res, path);
  if (!res.ok) throw new Error(await readError(res));

  const disposition = res.headers.get("content-disposition") || "";
  const match = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
  const filename = match ? decodeURIComponent(match[1]) : fallbackName;

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}