/**
 * Feedback tras 401 en apiClient: el redirect a /login ocurre antes de que React monte,
 * así que guardamos un mensaje breve en sessionStorage para mostrarlo en Login.
 */

export const AUTH_SESSION_END_STORAGE_KEY = "digiz_auth_session_end_v1";

export type SessionEndReason = "expired" | "invalid" | "missing" | "unknown";

export type SessionEndPayload = {
  reason: SessionEndReason;
  /** ISO backend msg (opcional, solo diagnóstico). */
  detail?: string;
};

/** Interpreta el cuerpo típico de Flask-JWT-Extended (`{ "msg": "..." }`). */
export function parseJwt401Reason(data: unknown): SessionEndReason {
  const msg =
    typeof data === "object" && data !== null && "msg" in data
      ? String((data as { msg: unknown }).msg).toLowerCase()
      : "";
  if (!msg) return "unknown";
  if (msg.includes("expired") || msg.includes("expir")) return "expired";
  if (
    msg.includes("invalid") ||
    msg.includes("not enough segments") ||
    msg.includes("signature") ||
    msg.includes("decode") ||
    msg.includes("malformed")
  ) {
    return "invalid";
  }
  if (msg.includes("missing") || msg.includes("authorization required") || msg.includes("authorization header")) {
    return "missing";
  }
  return "unknown";
}

export function setSessionEndFeedback(payload: SessionEndPayload): void {
  try {
    sessionStorage.setItem(AUTH_SESSION_END_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    /* storage bloqueado / privado */
  }
}

/** Lee y borra el mensaje (un solo uso). */
export function consumeSessionEndFeedback(): SessionEndPayload | null {
  try {
    const raw = sessionStorage.getItem(AUTH_SESSION_END_STORAGE_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(AUTH_SESSION_END_STORAGE_KEY);
    const parsed = JSON.parse(raw) as SessionEndPayload;
    if (!parsed || typeof parsed.reason !== "string") return null;
    return parsed;
  } catch {
    return null;
  }
}

export function sessionEndUserMessage(reason: SessionEndReason): string {
  switch (reason) {
    case "expired":
      return "Tu sesión expiró. Volvé a iniciar sesión para continuar.";
    case "invalid":
      return "La sesión dejó de ser válida (por ejemplo, tras un cambio en el servidor). Volvé a iniciar sesión.";
    case "missing":
      return "No hay una sesión activa. Iniciá sesión para continuar.";
    default:
      return "Tu sesión finalizó. Volvé a iniciar sesión para continuar.";
  }
}
