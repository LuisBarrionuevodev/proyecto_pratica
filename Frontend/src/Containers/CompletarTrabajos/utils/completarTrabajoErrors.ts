import {
  ACTUACION_FIELD_ERROR_SUMMARY,
  feedbackSeverityForActuacionError,
  normalizeActuacionApiError,
} from "../../Actuaciones/validations/normalizeActuacionApiError";
import type { FeedbackSeverity } from "../../../components/feedback/GlobalFeedbackProvider";

/** Texto breve del toast cuando hay errores inline en Completar trabajo. */
export const COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY = ACTUACION_FIELD_ERROR_SUMMARY;

const COMPLETAR_FALLBACK = "No se pudo guardar el cierre.";

/**
 * Convierte la respuesta de error del cierre en mensaje general breve + mapa por campo para inline.
 */
export function applyCompletarTrabajoFieldErrorsFromApi(err: unknown): {
  fieldErrors: Record<string, string>;
  generalMessage: string | null;
  severity: FeedbackSeverity;
} {
  const normalized = normalizeActuacionApiError(err, {
    fallbackMessage: COMPLETAR_FALLBACK,
    fieldErrorSummary: COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY,
  });
  return {
    fieldErrors: normalized.fieldErrors,
    generalMessage: normalized.message || null,
    severity: feedbackSeverityForActuacionError(normalized.kind),
  };
}

/**
 * Formatea errores del cierre Completar trabajo (400 detail o 422 errors por campo).
 * Solo para errores globales sin mapa por campo.
 */
export function formatCompletarTrabajoApiError(err: unknown): string {
  return normalizeActuacionApiError(err, {
    fallbackMessage: COMPLETAR_FALLBACK,
    fieldErrorSummary: COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY,
  }).message;
}

/**
 * Si el backend devolvió 422 con mapa por campo, retorna ese mapa; si no, null.
 */
export function parseCompletarTrabajoFieldErrors(err: unknown): Record<string, string> | null {
  const normalized = normalizeActuacionApiError(err, { fallbackMessage: COMPLETAR_FALLBACK });
  if (Object.keys(normalized.fieldErrors).length === 0) return null;
  return normalized.fieldErrors;
}
