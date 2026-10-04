export type CompletarTrabajoFinalizeFlowResult =
  | "validation_failed"
  | "upload_failed"
  | "cierre_failed"
  | "success";

export type CompletarTrabajoFinalizeFlowDeps = {
  validate: () => { canSubmit: boolean; fieldErrors: Record<string, string> };
  uploadPendingMedia: () => Promise<boolean>;
  submitCierre: () => Promise<void>;
};

/**
 * Orden estricto: validar → subir evidencia pendiente → cerrar trabajo.
 */
export async function runCompletarTrabajoFinalizeFlow(
  deps: CompletarTrabajoFinalizeFlowDeps
): Promise<CompletarTrabajoFinalizeFlowResult> {
  const validation = deps.validate();
  if (!validation.canSubmit) {
    return "validation_failed";
  }
  const uploaded = await deps.uploadPendingMedia();
  if (!uploaded) {
    return "upload_failed";
  }
  try {
    await deps.submitCierre();
    return "success";
  } catch {
    return "cierre_failed";
  }
}
