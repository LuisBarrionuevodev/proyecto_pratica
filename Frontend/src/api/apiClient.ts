import axios from "axios";

import {
  parseJwt401Reason,
  setSessionEndFeedback,
} from "../auth/sessionEndFeedback";

function resolveApiBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL?.trim();
  if (raw) {
    return raw.endsWith("/") ? raw : `${raw}/`;
  }
  if (import.meta.env.DEV) {
    return "http://localhost:5000/";
  }
  throw new Error(
    "VITE_API_BASE_URL no está definida. Configurarla en el build de producción/staging (URL del backend con barra final opcional)."
  );
}

export const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/** Rutas públicas que no deben forzar redirect por 401. */
const isAuthPublicUrl = (url: string | undefined) =>
  Boolean(url && (url.includes("/api/auth/login") || url.includes("/api/auth/password-reset")));

/**
 * Evita múltiples redirects si varias peticiones devuelven 401 a la vez.
 */
let authRedirectToLoginScheduled = false;

function scheduleAuthRedirectToLogin(reason: ReturnType<typeof parseJwt401Reason>, detail?: string): void {
  if (typeof window === "undefined") return;
  if (window.location.pathname.includes("/login")) return;
  if (authRedirectToLoginScheduled) return;
  authRedirectToLoginScheduled = true;
  setSessionEndFeedback({
    reason,
    detail,
  });
  window.location.assign("/login");
}

/**
 * 401 de Flask-JWT = token ausente, expirado o inválido. Limpia sesión, guarda motivo
 * para el login y redirige (sin refresh token en este proyecto).
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const reqUrl = error.config?.url ?? "";
    if (status === 401 && !isAuthPublicUrl(reqUrl)) {
      const data = error.response?.data;
      const msg =
        typeof data === "object" && data !== null && "msg" in data
          ? String((data as { msg: unknown }).msg)
          : undefined;
      const reason = parseJwt401Reason(data);
      localStorage.removeItem("access_token");
      scheduleAuthRedirectToLogin(reason, msg);
    }
    return Promise.reject(error);
  }
);
