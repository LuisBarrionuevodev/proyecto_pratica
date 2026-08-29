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

function firstStringMessage(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (Array.isArray(value)) {
    for (const item of value) {
      const s = firstStringMessage(item);
      if (s) return s;
    }
  }
  return null;
}

function pydanticArrayToFieldMap(errors: unknown[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const err of errors) {
    if (!isRecord(err)) continue;
    const loc = err.loc;
    const msg = firstStringMessage(err.msg) ?? "Error";
    if (Array.isArray(loc) && loc.length > 0) {
      const field = String(loc[loc.length - 1]);
      if (!out[field]) out[field] = msg;
      continue;
    }
    if (!out._row) out._row = msg;
  }
  return out;
}

function stringFieldErrors(raw: Record<string, unknown>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(raw)) {
    const msg = firstStringMessage(v);
    if (msg) out[k] = msg;
  }
  return out;
}

function extractRawFieldErrors(data: Record<string, unknown>): Record<string, string> | undefined {
  const errorsRaw = data.errors;
  if (Array.isArray(errorsRaw) && errorsRaw.length > 0) {
    const mapped = pydanticArrayToFieldMap(errorsRaw);
    return Object.keys(mapped).length > 0 ? mapped : undefined;
  }
  if (isRecord(errorsRaw) && Object.keys(errorsRaw).length > 0) {
    const mapped = stringFieldErrors(errorsRaw);
    return Object.keys(mapped).length > 0 ? mapped : undefined;
  }
  return undefined;
}

/** Intenta mapear mensajes de negocio (400 detail) a un campo cuando el backend no envía `errors`. */
export function mapBusinessDetailToFieldErrors(message: string): Record<string, string> | null {
  const m = message.toLowerCase();
  if (
    m.includes("numero_oficio") ||
    (m.includes("número") && m.includes("oficio")) ||
    (m.includes("numero") && m.includes("oficio") && m.includes("existe"))
  ) {
    return { numero_oficio: message };
  }
  if (m.includes("causa")) return { causa: message };
  if (m.includes("juzgado")) return { juzgado_id: message };
  if (m.includes("expediente")) return { numero_expediente_oficio: message };
  if (m.includes("contraproducencia")) return { contraproducencia: message };
  if (m.includes("resultado de cumplimiento")) return { resultado_cumplimiento_oficio: message };
  if (m.includes("nueva inspección") || m.includes("nueva inspeccion") || m.includes("quitar las actas")) {
    return { realizo_nueva_inspeccion: message };
  }
  if (m.includes("rubro")) return { rubro_nombre: message };
  if (m.includes("domicilio") || m.includes("calle")) return { calle: message };
  return null;
}

/**
 * Extrae `detail` y `errors` típicos de respuestas Flask/Pydantic vía axios.
 */
export function parseApiError(err: unknown, fallbackMessage = "Ocurrió un error."): ParsedApiError {
  const ax = err as { response?: { data?: unknown } };
  const data = ax?.response?.data;

  if (isRecord(data)) {
    const rawFieldErrors = extractRawFieldErrors(data);

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
      rowChunks.length > 0 ? `${fieldErrorSummary} ${rowChunks.join(" ")}`.trim() : fieldErrorSummary;
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

  const detailFields = mapBusinessDetailToFieldErrors(parsed.message);
  if (detailFields) {
    return {
      fieldErrors: detailFields,
      globalMessage: options.fieldErrorSummary ?? DEFAULT_FIELD_ERROR_SUMMARY,
    };
  }

  return { fieldErrors: {}, globalMessage: parsed.message || fallback };
}

/** HTTP status de una respuesta axios, si existe. */
export function getHttpStatusFromApiError(err: unknown): number | undefined {
  return (err as { response?: { status?: number } })?.response?.status;
}

/**
 * Indica si el error corresponde a validación de entrada (400/422) sin cambio persistido.
 */
export function isApiValidationError(err: unknown): boolean {
  const status = getHttpStatusFromApiError(err);
  return status === 422 || status === 400;
}

export type MapApiErrorsToFormStateOptions = ApplyFormErrorsOptions;

/**
 * Punto único: parsea error HTTP → errores por campo + mensaje global breve (sin duplicar inline).
 */
export function mapApiErrorsToFormState(
  err: unknown,
  options: MapApiErrorsToFormStateOptions = {}
): FormErrorsFromApi {
  return applyFormErrorsFromApi(err, options);
}
