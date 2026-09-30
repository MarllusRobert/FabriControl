export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8040";
const TOKEN_KEY = "fabricontrol_token";

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error("Não foi possível falar com o servidor. Confira se a API está no ar.");
  }
  if (response.status === 401 && !path.startsWith("/auth/login") && !path.startsWith("/setup")) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new Error("Sessão expirada. Entre novamente.");
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = data.detail;
    throw new Error(typeof detail === "string" ? detail : "Não foi possível concluir.");
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
