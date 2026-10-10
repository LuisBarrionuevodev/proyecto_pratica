import {
  validateActuacionFormForSubmit,
  type ActuacionFormValidationContext,
  type ActuacionFormValidationInput,
  type ActuacionFormValidationResult,
} from "../../Actuaciones/validations/actuacionFormValidation";
import type { IItemActaInspeccionCatalogItem } from "../../../api/itemActaInspeccionCatalogApi";
import {
  validateTieneHabilitacionObligatoria,
  type ChecklistUxValue,
} from "../../Actuaciones/utils/inspeccionChecklistSubmit";
import {
  validateCompletarTrabajoSeguimientoFields,
  type CompletarTrabajoSeguimientoValidationInput,
} from "./actaSeguimientoUi";

export type CompletarTrabajoChecklistValidationInput = {
  requireTieneHabilitacion?: boolean;
  checklistEstados?: Record<number, ChecklistUxValue>;
  checklistCatalog?: IItemActaInspeccionCatalogItem[];
};

/**
 * Validación completa de Completar trabajo antes de subir evidencia o cerrar.
 */
export function mergeCompletarTrabajoSubmitValidation(
  form: ActuacionFormValidationInput,
  context: ActuacionFormValidationContext,
  seguimiento: CompletarTrabajoSeguimientoValidationInput,
  checklist?: CompletarTrabajoChecklistValidationInput
): ActuacionFormValidationResult {
  const base = validateActuacionFormForSubmit(form, context);
  const segErrors = validateCompletarTrabajoSeguimientoFields(seguimiento);
  const fieldErrors = { ...base.fieldErrors, ...segErrors };
  if (checklist?.requireTieneHabilitacion) {
    const msg = validateTieneHabilitacionObligatoria(
      checklist.checklistEstados ?? {},
      checklist.checklistCatalog ?? []
    );
    if (msg) fieldErrors.items_acta_inspeccion = msg;
  }
  const canSubmit =
    base.canSubmit && Object.keys(segErrors).length === 0 && Object.keys(fieldErrors).length === 0;
  return {
    ...base,
    fieldErrors,
    canSubmit,
    globalError: canSubmit ? base.globalError : base.globalError,
  };
}
