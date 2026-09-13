import type { ItemInspeccionEstadoUx } from "../../Actuaciones/utils/inspeccionChecklistSubmit";

export const CARGAR_ACTUACION_SUCCESS_MESSAGE = "Actuación guardada correctamente.";

export type CargarActuacionChecklistV2ResetState = {
  checklistEstados: Record<number, ItemInspeccionEstadoUx>;
  personasSinCarnet: string;
  checklistItemsTouched: boolean;
  personasSinCarnetTouched: boolean;
};

/**
 * Estado V2 vacío para checklist y personas sin carnet tras Limpiar o guardado exitoso.
 * NONE = ausencia de entrada en `checklistEstados` (no reconstruir desde catálogo).
 */
export function getCargarActuacionChecklistV2ResetState(): CargarActuacionChecklistV2ResetState {
  return {
    checklistEstados: {},
    personasSinCarnet: "0",
    checklistItemsTouched: false,
    personasSinCarnetTouched: false,
  };
}

/**
 * Feedback de éxito y cleanup UI post-commit; errores locales no se propagan al caller.
 */
export function runCargarActuacionPostSaveCleanup(actions: {
  success: (message: string) => void;
  resetForm: () => void;
  closeModal: () => void;
  logError?: (message: string, error: unknown) => void;
}): void {
  actions.success(CARGAR_ACTUACION_SUCCESS_MESSAGE);
  try {
    actions.resetForm();
    actions.closeModal();
  } catch (uiError) {
    const log = actions.logError ?? ((message, error) => console.error(message, error));
    log("Error limpiando Cargar Actuación tras guardado exitoso", uiError);
  }
}
