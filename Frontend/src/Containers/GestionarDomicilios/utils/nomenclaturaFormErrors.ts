import { applyFormErrorsFromApi } from "../../../utils/parseApiError";

const NOMENCLATURA_FIELD_ALIASES: Record<string, string> = {
  calle_input: "calle_input",
  calle: "calle_input",
  numero: "numero",
  numero_tipo: "numero_tipo",
  esquina: "numero",
};

const NOMENCLATURA_FORM_OPTIONS = {
  fieldKeyAliases: NOMENCLATURA_FIELD_ALIASES,
  fallbackMessage: "No se pudo guardar la nomenclatura.",
} as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * El endpoint de nomenclatura devuelve 422 con `detail` como array Pydantic (no `errors`).
 */
function coerceNomenclaturaApiError(err: unknown): unknown {
  const ax = err as { response?: { status?: number; data?: unknown } };
  const data = ax?.response?.data;
  if (!isRecord(data)) return err;
  const detail = data.detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return {
      ...ax,
      response: {
        ...ax.response,
        data: { errors: detail },
      },
    };
  }
  return err;
}

/**
 * Mapea errores API de guardar nomenclatura a errores de campo + mensaje global (STAB-5).
 */
export function applyNomenclaturaErrorsFromApi(err: unknown): {
  fieldErrors: Record<string, string>;
  globalMessage: string | null;
} {
  return applyFormErrorsFromApi(coerceNomenclaturaApiError(err), NOMENCLATURA_FORM_OPTIONS);
}

/**
 * Error de validación local antes del request (p. ej. número vacío).
 */
export function nomenclaturaClientFieldError(message: string): {
  fieldErrors: Record<string, string>;
  globalMessage: string | null;
} {
  return {
    fieldErrors: { numero: message },
    globalMessage: null,
  };
}

/**
 * Errores de validación local antes del request HTTP.
 */
export function mapClientNomenclaturaError(message: string): {
  fieldErrors: Record<string, string>;
  globalMessage: string | null;
} {
  const lower = message.toLowerCase();
  if (lower.includes("número") || lower.includes("numero") || lower.includes("esquina")) {
    return nomenclaturaClientFieldError(message);
  }
  if (lower.includes("calle")) {
    return { fieldErrors: { calle_input: message }, globalMessage: null };
  }
  return { fieldErrors: {}, globalMessage: message };
}
