export type CompletarTrabajoFinalizeFlowResult =
  | "validation_failed"
  | "cierre_failed"
  | "success"
  | "success_evidencias_pendientes";

export type CompletarTrabajoFinalizeFlowOutcome = {
  flow: CompletarTrabajoFinalizeFlowResult;
  cierreError?: unknown;
};

export type CompletarTrabajoFinalizeFlowDeps = {
  validate: () => { canSubmit: boolean; fieldErrors: Record<string, string> };
  submitCierre: () => Promise<void>;
  uploadPendingMedia?: () => Promise<boolean>;
  hasPendingUpload?: () => boolean;
};

const CIERRE_NETWORK_MESSAGE =
  "No se pudo confirmar el guardado. Revisá tu conexión y reintentá.";

export function isLikelyNetworkCierreError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const msg = String((error as { message?: string }).message ?? "").toLowerCase();
  if (msg.includes("network error") || msg.includes("failed to fetch")) return true;
  const code = (error as { code?: string }).code;
  return code === "ERR_NETWORK";
}

export { CIERRE_NETWORK_MESSAGE };

/**
 * Orden estricto: validar → cerrar trabajo (alfanumérico) → subir evidencias pendientes.
 */
export async function runCompletarTrabajoFinalizeFlow(
  deps: CompletarTrabajoFinalizeFlowDeps
): Promise<CompletarTrabajoFinalizeFlowOutcome> {
  const validation = deps.validate();
  if (!validation.canSubmit) {
    return { flow: "validation_failed" };
  }
  try {
    await deps.submitCierre();
  } catch (e) {
    return { flow: "cierre_failed", cierreError: e };
  }
  const pending = deps.hasPendingUpload?.() ?? false;
  if (!pending) {
    return { flow: "success" };
  }
  const uploaded = await (deps.uploadPendingMedia?.() ?? Promise.resolve(true));
  if (!uploaded) {
    return { flow: "success_evidencias_pendientes" };
  }
  return { flow: "success" };
}
