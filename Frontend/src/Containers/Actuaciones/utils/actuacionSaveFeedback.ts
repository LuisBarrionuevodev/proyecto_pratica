import type { AppFeedback, FeedbackSeverity } from "../../../components/feedback/GlobalFeedbackProvider";
import { ACTUACION_FIELD_LABELS } from "./actuacionFormErrors";
import type { ActuacionFormValidationResult } from "../validations/actuacionFormValidation";
import type { SubmitActuacionRowResult } from "./submitActuacionRow";

export const MENSAJE_GUARDADO_OK = "Actuación guardada correctamente.";
export const MENSAJE_CORRECCION_OK = "Actuación corregida correctamente.";
export const MENSAJE_VALIDACION_LOCAL = "Revisá los campos marcados antes de guardar.";
export const MENSAJE_ERROR_GRAVE = "No se pudo guardar la actuación.";

/**
 * Arma el mensaje del popup superior para errores de guardado.
 * Prioriza resumen con nombres de campo; evita textos genéricos sin contexto.
 */
export function buildActuacionSaveFeedbackMessage(result: SubmitActuacionRowResult): {
  severity: FeedbackSeverity;
  message: string;
} | null {
  if (result.ok) {
    return {
      severity: "success",
      message: result.correccionCierre ? MENSAJE_CORRECCION_OK : MENSAJE_GUARDADO_OK,
    };
  }

  if (result.kind === "reingreso_blocked") {
    return { severity: "warning", message: result.message };
  }

  if (result.kind === "validation" || result.kind === "backend_fields") {
    const global = result.globalMessage?.trim();
    if (global?.startsWith("Revisá:")) {
      return { severity: "warning", message: global };
    }
    const labels = Object.keys(result.fieldErrors)
      .filter((k) => result.fieldErrors[k]?.trim())
      .map((k) => ACTUACION_FIELD_LABELS[k] ?? k);
    if (labels.length > 0) {
      return { severity: "warning", message: `Revisá: ${labels.join(", ")}.` };
    }
    if (global) {
      return { severity: "warning", message: global };
    }
    return { severity: "warning", message: MENSAJE_VALIDACION_LOCAL };
  }

  return {
    severity: "error",
    message: result.message?.trim() || MENSAJE_ERROR_GRAVE,
  };
}

/**
 * Emite toasts unificados según el resultado de guardar una actuación.
 * Los errores de campo van solo inline (rojo + helperText); el popup resume arriba.
 */
export function notifyActuacionSaveResult(result: SubmitActuacionRowResult, feedback: AppFeedback): void {
  const payload = buildActuacionSaveFeedbackMessage(result);
  if (!payload) return;
  feedback[payload.severity](payload.message);
}

/**
 * Emite popup superior para errores de validación cliente (sin Alert duplicado en modal).
 */
export function notifyActuacionFormValidationResult(
  result: ActuacionFormValidationResult,
  feedback: AppFeedback
): void {
  if (result.canSubmit) return;
  const global = result.globalError?.trim();
  if (global?.startsWith("Revisá:")) {
    feedback.warning(global);
    return;
  }
  const labels = Object.keys(result.fieldErrors)
    .filter((k) => result.fieldErrors[k]?.trim())
    .map((k) => ACTUACION_FIELD_LABELS[k] ?? k);
  if (labels.length > 0) {
    feedback.warning(`Revisá: ${labels.join(", ")}.`);
    return;
  }
  feedback.warning(global || MENSAJE_VALIDACION_LOCAL);
}
