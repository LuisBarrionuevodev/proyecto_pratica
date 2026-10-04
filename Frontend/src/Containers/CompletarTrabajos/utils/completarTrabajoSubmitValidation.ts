import {
  validateActuacionFormForSubmit,
  type ActuacionFormValidationContext,
  type ActuacionFormValidationInput,
  type ActuacionFormValidationResult,
} from "../../Actuaciones/validations/actuacionFormValidation";
import {
  validateCompletarTrabajoSeguimientoFields,
  type CompletarTrabajoSeguimientoValidationInput,
} from "./actaSeguimientoUi";

/**
 * Validación completa de Completar trabajo antes de subir evidencia o cerrar.
 */
export function mergeCompletarTrabajoSubmitValidation(
  form: ActuacionFormValidationInput,
  context: ActuacionFormValidationContext,
  seguimiento: CompletarTrabajoSeguimientoValidationInput
): ActuacionFormValidationResult {
  const base = validateActuacionFormForSubmit(form, context);
  const segErrors = validateCompletarTrabajoSeguimientoFields(seguimiento);
  const fieldErrors = { ...base.fieldErrors, ...segErrors };
  const canSubmit = base.canSubmit && Object.keys(segErrors).length === 0;
  return {
    ...base,
    fieldErrors,
    canSubmit,
    globalError: canSubmit ? base.globalError : base.globalError,
  };
}
