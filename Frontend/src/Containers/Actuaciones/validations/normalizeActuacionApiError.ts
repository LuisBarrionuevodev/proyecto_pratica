import type { FeedbackSeverity } from "../../../components/feedback/GlobalFeedbackProvider";
import {
  DEFAULT_FIELD_ERROR_SUMMARY,
  getHttpStatusFromApiError,
  mapBusinessDetailToFieldErrors,
  parseApiError,
} from "../../../utils/parseApiError";
import { ACTUACION_ROW_ERROR_KEY_MAP } from "./actuacionApiFieldKeyMap";

export const ACTUACION_NETWORK_ERROR_MESSAGE = "No se pudo conectar con el servidor.";

export const ACTUACION_FIELD_ERROR_SUMMARY = "Revisá los campos marcados.";

export type NormalizedActuacionErrorKind = "validation" | "conflict" | "server" | "network";

export type NormalizedActuacionError = {
  status?: number;
  kind: NormalizedActuacionErrorKind;
  message: string;
  fieldErrors: Record<string, string>;
  rowMessages: string[];
};

/** Validadores Pydantic cuyo mensaje es global, no de un input. */
export const ACTUACION_ROW_ONLY_VALIDATOR_KEYS = new Set<string>([
  "_row",
  "_global",
  "detail",
  "no_actas_si_visita_no_realizada",
]);

/** Alias API → campo del formulario (snake_case interno). */
export const ACTUACION_API_FIELD_KEY_ALIASES: Record<string, string> = {
  comprobacion_exige_motivo_si_hay_acta: "comprobacion_motivo",
  notificacion_exige_motivo_si_hay_acta: "notificacion_motivo_1",
};

const ACTA_NESTED_SEGMENT_TO_FIELD: Record<string, string> = {
  inspeccion: "acta_inspeccion_num",
  inspección: "acta_inspeccion_num",
  comprobacion: "acta_comprobacion_num",
  comprobación: "acta_comprobacion_num",
  notificacion: "acta_notificacion_num",
  notificación: "acta_notificacion_num",
  clausura: "acta_clausura_num",
  decomiso: "acta_decomiso_num",
};

const META_FIELD_KEYS = new Set(["_row", "_global", "detail"]);

function normalizeSegment(segment: string): string {
  return segment.trim().toLowerCase().normalize("NFD").replace(/\p{M}/gu, "");
}

/**
 * Resuelve paths anidados `actas.{tipo}.*` al campo de formulario correcto.
 *
 * @returns Clave interna, `_row` si el path es ambiguo, o null si no es path de actas.
 */
export function mapActuacionNestedActaKey(key: string): string | "_row" | null {
  if (!key.startsWith("actas.")) return null;
  const parts = key.split(".");
  if (parts.length < 2) return "_row";
  const segment = parts[1];
  if (/^\d+$/.test(segment)) return "_row";
  const normalized = normalizeSegment(segment);
  for (const [tipo, field] of Object.entries(ACTA_NESTED_SEGMENT_TO_FIELD)) {
    if (normalizeSegment(tipo) === normalized || normalized.includes(normalizeSegment(tipo))) {
      return field;
    }
  }
  return "_row";
}

/**
 * Traduce una clave de error API / Glide / Pydantic al campo interno del formulario.
 *
 * @param key Clave cruda del backend o grilla.
 * @returns Campo destino o `_row` para errores globales / ambiguos.
 */
export function mapActuacionApiFieldKey(key: string): string {
  if (META_FIELD_KEYS.has(key)) return key;
  if (key in ACTUACION_ROW_ERROR_KEY_MAP) return ACTUACION_ROW_ERROR_KEY_MAP[key];
  if (key === "motivo") return "_row";
  const nested = mapActuacionNestedActaKey(key);
  if (nested != null) return nested;
  if (key in ACTUACION_API_FIELD_KEY_ALIASES) return ACTUACION_API_FIELD_KEY_ALIASES[key];
  return key;
}

export type NormalizeActuacionApiErrorOptions = {
  fallbackMessage?: string;
  fieldErrorSummary?: string;
  rowOnlyKeys?: ReadonlySet<string>;
  extraFieldKeyAliases?: Record<string, string>;
};

function classifyKind(status?: number): NormalizedActuacionErrorKind {
  if (status == null) return "network";
  if (status === 409) return "conflict";
  if (status === 400 || status === 422) return "validation";
  if (status >= 500) return "server";
  if (status >= 400) return "validation";
  return "server";
}

function splitNormalizedErrors(
  raw: Record<string, string>,
  options: NormalizeActuacionApiErrorOptions
): { fieldErrors: Record<string, string>; rowMessages: string[] } {
  const rowOnly = new Set([...ACTUACION_ROW_ONLY_VALIDATOR_KEYS, ...(options.rowOnlyKeys ?? [])]);
  const fieldErrors: Record<string, string> = {};
  const rowMessages: string[] = [];

  for (const [rawKey, rawMsg] of Object.entries(raw)) {
    const msg = rawMsg?.trim();
    if (!msg) continue;
    const alias = options.extraFieldKeyAliases?.[rawKey];
    const mappedKey = alias ?? mapActuacionApiFieldKey(rawKey);
    if (rowOnly.has(rawKey) || rowOnly.has(mappedKey) || mappedKey === "_row") {
      rowMessages.push(msg);
      continue;
    }
    fieldErrors[mappedKey] = msg;
  }

  return { fieldErrors, rowMessages };
}

function buildHumanMessage(
  kind: NormalizedActuacionErrorKind,
  fieldErrors: Record<string, string>,
  rowMessages: string[],
  detailMessage: string,
  fieldErrorSummary: string,
  fallbackMessage: string
): string {
  if (rowMessages.length > 0 && Object.keys(fieldErrors).length === 0) {
    return rowMessages.join(" ");
  }
  if (Object.keys(fieldErrors).length > 0) {
    return rowMessages.length > 0
      ? `${fieldErrorSummary} ${rowMessages.join(" ")}`.trim()
      : fieldErrorSummary;
  }
  if (detailMessage && detailMessage !== "Validation error") {
    return detailMessage;
  }
  if (kind === "network") return ACTUACION_NETWORK_ERROR_MESSAGE;
  return fallbackMessage;
}

/**
 * Normaliza un error HTTP/Axios del dominio actuaciones.
 * Siempre recibir el error original (nunca un ParsedApiError).
 */
export function normalizeActuacionApiError(
  err: unknown,
  options: NormalizeActuacionApiErrorOptions = {}
): NormalizedActuacionError {
  const fallbackMessage = options.fallbackMessage ?? "Ocurrió un error.";
  const fieldErrorSummary = options.fieldErrorSummary ?? ACTUACION_FIELD_ERROR_SUMMARY;
  const status = getHttpStatusFromApiError(err);
  const hasResponse = (err as { response?: unknown })?.response != null;

  if (!hasResponse) {
    return {
      status,
      kind: "network",
      message: ACTUACION_NETWORK_ERROR_MESSAGE,
      fieldErrors: {},
      rowMessages: [],
    };
  }

  const kind = classifyKind(status);
  const parsed = parseApiError(err, fallbackMessage);

  if (parsed.rawFieldErrors && Object.keys(parsed.rawFieldErrors).length > 0) {
    const { fieldErrors, rowMessages } = splitNormalizedErrors(parsed.rawFieldErrors, options);
    return {
      status,
      kind,
      message: buildHumanMessage(
        kind,
        fieldErrors,
        rowMessages,
        parsed.message,
        fieldErrorSummary,
        fallbackMessage
      ),
      fieldErrors,
      rowMessages,
    };
  }

  const detailFields = mapBusinessDetailToFieldErrors(parsed.message);
  if (detailFields) {
    const { fieldErrors, rowMessages } = splitNormalizedErrors(detailFields, options);
    return {
      status,
      kind,
      message: fieldErrorSummary,
      fieldErrors,
      rowMessages,
    };
  }

  const message =
    parsed.message === "Network Error"
      ? fallbackMessage
      : parsed.message || fallbackMessage;

  return {
    status,
    kind,
    message,
    fieldErrors: {},
    rowMessages: message ? [message] : [],
  };
}

/** Severidad de toast según tipo de error normalizado. */
export function feedbackSeverityForActuacionError(
  kind: NormalizedActuacionErrorKind
): FeedbackSeverity {
  if (kind === "validation" || kind === "conflict") return "warning";
  return "error";
}

/** @deprecated Usar ACTUACION_FIELD_ERROR_SUMMARY */
export const DEFAULT_ACTUACION_FIELD_ERROR_SUMMARY = DEFAULT_FIELD_ERROR_SUMMARY;
