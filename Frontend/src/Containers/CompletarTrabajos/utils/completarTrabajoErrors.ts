/**
 * Si el backend devolvió 422 con mapa por campo, retorna ese mapa; si no, null.
 */
export function parseCompletarTrabajoFieldErrors(err: unknown): Record<string, string> | null {
  const ax = err as {
    response?: { data?: { errors?: Record<string, string> } };
  };
  const errs = ax?.response?.data?.errors;
  if (errs && typeof errs === "object" && Object.keys(errs).length > 0) {
    const out: Record<string, string> = {};
    for (const [k, v] of Object.entries(errs)) {
      if (typeof v === "string") out[k] = v;
    }
    return Object.keys(out).length > 0 ? out : null;
  }
  return null;
}

/**
 * Formatea errores del cierre Completar trabajo (400 detail o 422 errors por campo).
 */
export function formatCompletarTrabajoApiError(err: unknown): string {
  const ax = err as {
    response?: { data?: { detail?: string; errors?: Record<string, string> } };
  };
  const errs = ax?.response?.data?.errors;
  if (errs && typeof errs === "object" && Object.keys(errs).length > 0) {
    return Object.entries(errs)
      .map(([k, v]) => `${k}: ${v}`)
      .join("\n");
  }
  const d = ax?.response?.data?.detail;
  if (typeof d === "string") return d;
  return "No se pudo guardar el cierre.";
}
