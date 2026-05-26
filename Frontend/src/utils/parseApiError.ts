/**
 * Normalización de errores HTTP (400/422) para formularios y modales.
 *
 * Convención backend: `{ detail?: string, errors?: Record<string, string> }`
 * con claves de celda/campo y `_row` para validadores a nivel fila.
 */

export type ParsedApiError = {
  /** Mensaje global cuando no hay mapa por campo o como fallback. */
  message: string;
  /** Errores crudos del backend (`errors`), sin aliases. */
  rawFieldErrors?: Record<string, string>;
};

export type FormErrorsFromApi = {
  /** Mapa listo para `error` + `helperText` en inputs. */
  fieldErrors: Record<string, string>;
  /** Alert inline breve; null si no hace falta banner global. */
  globalMessage: string | null;
};

export type ApplyFormErrorsOptions = {
  /** Traduce claves API → nombre de campo del formulario. */
  fieldKeyAliases?: Record<string, string>;
  /** Validadores cuyo mensaje va al resumen, no a un input. */
  rowOnlyKeys?: ReadonlySet<string>;
  /** Texto del Alert cuando hay errores inline en campos. */
  fieldErrorSummary?: string;
  fallbackMessage?: string;
};

export const DEFAULT_FIELD_ERROR_SUMMARY = "Revisá los campos marcados abajo.";

const META_KEYS = new Set(["_row", "detail", "_global"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringFieldErrors(raw: Record<string, unknown>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(raw)) {
    if (typeof v === "string" && v.trim()) out[k] = v.trim();
  }
  return out;
}

/**
 * Extrae `detail` y `errors` típicos de respuestas Flask/Pydantic vía axios.
 */
export function parseApiError(err: unknown, fallbackMessage = "Ocurrió un error."): ParsedApiError {
  const ax = err as { response?: { data?: unknown } };
  const data = ax?.response?.data;

  if (isRecord(data)) {
    const errorsRaw = data.errors;
    const rawFieldErrors =
      isRecord(errorsRaw) && Object.keys(errorsRaw).length > 0
        ? stringFieldErrors(errorsRaw)
        : undefined;

    const detail = data.detail;
    if (typeof detail === "string" && detail.trim()) {
      return { message: detail.trim(), rawFieldErrors };
    }

    if (rawFieldErrors) {
      return { message: DEFAULT_FIELD_ERROR_SUMMARY, rawFieldErrors };
    }
  }

  if (err instanceof Error && err.message.trim()) {
    return { message: err.message.trim() };
  }

  return { message: fallbackMessage };
}

/**
 * Parte un mapa de errores API en campos de formulario + mensajes globales/fila.
 */
export function applyFormErrorsFromMap(
  errors: Record<string, string> | undefined,
  options: ApplyFormErrorsOptions = {}
): FormErrorsFromApi {
  const {
    fieldKeyAliases = {},
    rowOnlyKeys = new Set<string>(),
    fieldErrorSummary = DEFAULT_FIELD_ERROR_SUMMARY,
  } = options;

  if (!errors || Object.keys(errors).length === 0) {
    return { fieldErrors: {}, globalMessage: null };
  }

  const fieldErrors: Record<string, string> = {};
  const rowChunks: string[] = [];

  for (const [k, v] of Object.entries(errors)) {
    if (!v?.trim()) continue;
    if (k === "_row" || k === "_global" || k === "detail") {
      rowChunks.push(v);
      continue;
    }
    if (rowOnlyKeys.has(k)) {
      rowChunks.push(v);
      continue;
    }
    const target = fieldKeyAliases[k] ?? k;
    if (META_KEYS.has(target)) {
      rowChunks.push(v);
      continue;
    }
    fieldErrors[target] = v;
  }

  const hasInline = Object.keys(fieldErrors).length > 0;

  if (hasInline) {
    const globalMessage =
      rowChunks.length > 0 ? `${fieldErrorSummary}\n${rowChunks.join("\n")}` : fieldErrorSummary;
    return { fieldErrors, globalMessage };
  }

  if (rowChunks.length > 0) {
    return { fieldErrors: {}, globalMessage: rowChunks.join("\n") };
  }

  return { fieldErrors: {}, globalMessage: null };
}

/**
 * Combina `parseApiError` + `applyFormErrorsFromMap` para handlers `catch`.
 */
export function applyFormErrorsFromApi(
  err: unknown,
  options: ApplyFormErrorsOptions = {}
): FormErrorsFromApi {
  const fallback = options.fallbackMessage ?? "Ocurrió un error.";
  const parsed = parseApiError(err, fallback);

  if (parsed.rawFieldErrors) {
    return applyFormErrorsFromMap(parsed.rawFieldErrors, options);
  }

  return { fieldErrors: {}, globalMessage: parsed.message || fallback };
}
