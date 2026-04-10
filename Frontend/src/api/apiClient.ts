import axios from "axios";

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
 * 401 de Flask-JWT = token ausente, expirado o inválido. Limpia sesión y envía a login
 * (el usuario suele tener la SPA abierta sin `access_token` tras cerrar o expirar).
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const reqUrl = error.config?.url ?? "";
    if (status === 401 && !isAuthPublicUrl(reqUrl)) {
      localStorage.removeItem("access_token");
      if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  }
);
