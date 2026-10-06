export type CompletarTrabajoFinalizeFlowResult =
  | "validation_failed"
  | "cierre_failed"
  | "success"
  | "success_evidencias_pendientes";

export type CompletarTrabajoFinalizeFlowDeps = {
  validate: () => { canSubmit: boolean; fieldErrors: Record<string, string> };
  submitCierre: () => Promise<void>;
  uploadPendingMedia: () => Promise<boolean>;
  hasPendingUpload?: () => boolean;
};

/**
 * Orden estricto: validar → cerrar trabajo (alfanumérico) → subir evidencias pendientes.
 */
export async function runCompletarTrabajoFinalizeFlow(
  deps: CompletarTrabajoFinalizeFlowDeps
): Promise<CompletarTrabajoFinalizeFlowResult> {
  const validation = deps.validate();
  if (!validation.canSubmit) {
    return "validation_failed";
  }
  await deps.submitCierre();
  const pending = deps.hasPendingUpload?.() ?? true;
  if (!pending) {
    return "success";
  }
  const uploaded = await deps.uploadPendingMedia();
  if (!uploaded) {
    return "success_evidencias_pendientes";
  }
  return "success";
}
