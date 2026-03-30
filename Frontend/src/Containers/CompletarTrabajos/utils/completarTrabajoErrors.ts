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

/** Validadores Pydantic `model_validator` cuyo mensaje va al resumen, no a un input concreto. */
const ROW_ONLY_VALIDATORS = new Set(["no_actas_si_visita_no_realizada"]);

/** Claves de error API → campo del formulario (cuando el `loc` de Pydantic no coincide con el nombre del payload). */
const FIELD_KEY_ALIASES: Record<string, string> = {
  comprobacion_exige_motivo_si_hay_acta: "comprobacion_motivo",
};

/** Texto breve del Alert cuando hay errores inline en Completar trabajo. */
export const COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY = "Revisá los campos marcados abajo.";

/**
 * Convierte la respuesta de error del cierre en mensaje general breve + mapa por campo para inline.
 *
 * Parámetros: `err` típico de axios (response.data.errors / detail).
 * Retorno: `fieldErrors` para `error`/`helperText` en inputs; `generalMessage` para un Alert corto arriba.
 */
export function applyCompletarTrabajoFieldErrorsFromApi(err: unknown): {
  fieldErrors: Record<string, string>;
  generalMessage: string | null;
} {
  const parsed = parseCompletarTrabajoFieldErrors(err);
  if (!parsed) {
    return { fieldErrors: {}, generalMessage: formatCompletarTrabajoApiError(err) };
  }

  const fieldErrors: Record<string, string> = {};
  const rowChunks: string[] = [];

  for (const [k, v] of Object.entries(parsed)) {
    if (k === "_row") {
      rowChunks.push(v);
      continue;
    }
    if (ROW_ONLY_VALIDATORS.has(k)) {
      rowChunks.push(v);
      continue;
    }
    const target = FIELD_KEY_ALIASES[k] ?? k;
    fieldErrors[target] = v;
  }

  const hasInline = Object.keys(fieldErrors).length > 0;
  let generalMessage: string | null;
  if (hasInline) {
    generalMessage =
      rowChunks.length > 0
        ? `${COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY}\n${rowChunks.join("\n")}`
        : COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY;
  } else if (rowChunks.length > 0) {
    generalMessage = rowChunks.join("\n");
  } else {
    generalMessage = formatCompletarTrabajoApiError(err);
  }

  return { fieldErrors, generalMessage };
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
