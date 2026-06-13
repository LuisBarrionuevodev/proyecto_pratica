import {
  applyFormErrorsFromApi,
  applyFormErrorsFromMap,
  DEFAULT_FIELD_ERROR_SUMMARY,
  parseApiError,
} from "../../../utils/parseApiError";

/** Validadores Pydantic `model_validator` cuyo mensaje va al resumen, no a un input concreto. */
const ROW_ONLY_VALIDATORS = new Set(["no_actas_si_visita_no_realizada"]);

/** Claves de error API → campo del formulario (cuando el `loc` de Pydantic no coincide con el nombre del payload). */
const FIELD_KEY_ALIASES: Record<string, string> = {
  comprobacion_exige_motivo_si_hay_acta: "comprobacion_motivo",
  notificacion_exige_motivo_si_hay_acta: "notificacion_motivo_1",
};

/** Texto breve del Alert cuando hay errores inline en Completar trabajo. */
export const COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY = DEFAULT_FIELD_ERROR_SUMMARY;

const COMPLETAR_OPTIONS = {
  fieldKeyAliases: FIELD_KEY_ALIASES,
  rowOnlyKeys: ROW_ONLY_VALIDATORS,
  fieldErrorSummary: COMPLETAR_TRABAJO_FIELD_ERROR_SUMMARY,
  fallbackMessage: "No se pudo guardar el cierre.",
} as const;

/**
 * Si el backend devolvió 422 con mapa por campo, retorna ese mapa; si no, null.
 */
export function parseCompletarTrabajoFieldErrors(err: unknown): Record<string, string> | null {
  const parsed = parseApiError(err, COMPLETAR_OPTIONS.fallbackMessage);
  if (!parsed.rawFieldErrors || Object.keys(parsed.rawFieldErrors).length === 0) return null;
  return parsed.rawFieldErrors;
}

/**
 * Convierte la respuesta de error del cierre en mensaje general breve + mapa por campo para inline.
 */
export function applyCompletarTrabajoFieldErrorsFromApi(err: unknown): {
  fieldErrors: Record<string, string>;
  generalMessage: string | null;
} {
  const { fieldErrors, globalMessage } = applyFormErrorsFromApi(err, COMPLETAR_OPTIONS);
  if (Object.keys(fieldErrors).length > 0) {
    return { fieldErrors, generalMessage: globalMessage };
  }
  return { fieldErrors, generalMessage: globalMessage ?? formatCompletarTrabajoApiError(err) };
}

/**
 * Formatea errores del cierre Completar trabajo (400 detail o 422 errors por campo).
 * Solo para errores globales sin mapa por campo.
 */
export function formatCompletarTrabajoApiError(err: unknown): string {
  const parsed = parseApiError(err, COMPLETAR_OPTIONS.fallbackMessage);
  if (parsed.rawFieldErrors) {
    const { globalMessage } = applyFormErrorsFromMap(parsed.rawFieldErrors, COMPLETAR_OPTIONS);
    if (globalMessage) return globalMessage;
  }
  return parsed.message;
}
