import type { ICompletarTrabajoDetalleResponse } from "../../../api/completarTrabajoApi";
import { COMPLETAR_TRABAJO_FOTOS_SUCCESS_MESSAGE } from "./completarTrabajoSoloEvidenciasMediaUpload";
import { isLocalCompletarTrabajoMediaQueueFinished } from "./completarTrabajoEvidenciasConfirm";
import { waitForCompletarTrabajoEvidenciasBackendSync } from "./completarTrabajoMediaPostUploadSync";
import type { CompletarTrabajoSoloEvidenciasMediaUploadDeps } from "./completarTrabajoSoloEvidenciasMediaUpload";
import { runCompletarTrabajoSoloEvidenciasMediaUpload } from "./completarTrabajoSoloEvidenciasMediaUpload";
import { countUploadableQueueItems } from "../../../features/media/utils/actuacionManualMediaSave";
import type { ManualMediaSaveResult } from "../../../features/media/utils/actuacionManualMediaSave";

export { COMPLETAR_TRABAJO_FOTOS_SUCCESS_MESSAGE };

export type CompletarTrabajoRecoveredUploadSuccessActions = {
  clearTransientErrors: () => void;
  clearUploadState: () => void;
  invalidateEvidenciasPendientesLocal: () => void;
  notifyPendientesRefresh: () => void;
  showSuccessToast: () => void;
  removeFromList: (rutaItemId: number) => void;
  closeModal: () => void;
  clearUploadPanelHold?: () => void;
};

/**
 * Cierre definitivo tras carga recuperada (misma semántica que Mis trabajos + sync de pendientes).
 */
export function applyCompletarTrabajoRecoveredUploadSuccess(
  rutaItemId: number,
  actions: CompletarTrabajoRecoveredUploadSuccessActions
): void {
  actions.clearTransientErrors();
  actions.clearUploadPanelHold?.();
  actions.clearUploadState();
  actions.notifyPendientesRefresh();
  actions.showSuccessToast();
  actions.removeFromList(rutaItemId);
  actions.closeModal();
  actions.invalidateEvidenciasPendientesLocal();
}

/** Solo evidencias: subir si hay cola uploadable; si no, confirmar cierre definitivo. */
export async function runCompletarTrabajoSoloEvidenciasFlow(
  deps: CompletarTrabajoSoloEvidenciasMediaUploadDeps
): Promise<ManualMediaSaveResult> {
  const uploadable = countUploadableQueueItems(deps.getQueueItems());
  if (uploadable > 0) {
    return runCompletarTrabajoSoloEvidenciasMediaUpload(deps);
  }
  return confirmCompletarTrabajoEvidenciasDefinitiveSuccess(deps);
}

/**
 * Cola local finalizada (p. ej. panel 3/3) sin ítems uploadable: reconsulta backend y cierra si corresponde.
 */
export async function confirmCompletarTrabajoEvidenciasDefinitiveSuccess(
  deps: CompletarTrabajoSoloEvidenciasMediaUploadDeps
): Promise<ManualMediaSaveResult> {
  const localFinished = isLocalCompletarTrabajoMediaQueueFinished(deps.getQueueItems());
  if (!localFinished && deps.getQueueItems().length > 0) {
    return { outcome: "partial", refreshFailed: false };
  }

  const sync = await waitForCompletarTrabajoEvidenciasBackendSync(deps.rutaItemId, {
    fetchDetalle: deps.fetchDetalleForConfirm,
    fetchArchivos: deps.fetchArchivosForReconcile,
  });
  const backendOk = sync.status === "completo";

  if (backendOk && (localFinished || deps.getQueueItems().length === 0)) {
    deps.clearUploadedFromQueue();
    return { outcome: "success", refreshFailed: false };
  }

  if (!backendOk && localFinished) {
    return { outcome: "partial", refreshFailed: false };
  }

  return { outcome: "empty", refreshFailed: false };
}

/** Ajuste de fila/detalle local para no mostrar banners de evidencias obsoletos antes del cierre. */
export function patchRowSinEvidenciasPendientes<
  T extends {
    trabajo_guardado_evidencias_pendientes?: boolean;
    media_resumen?: {
      tiene_evidencias_pendientes?: boolean;
      evidencias_pendientes_total?: number;
    };
  },
>(row: T): T {
  return {
    ...row,
    trabajo_guardado_evidencias_pendientes: false,
    media_resumen: {
      ...row.media_resumen,
      tiene_evidencias_pendientes: false,
      evidencias_pendientes_total: 0,
    },
  };
}

export function patchDetalleSinEvidenciasPendientes(
  det: ICompletarTrabajoDetalleResponse
): ICompletarTrabajoDetalleResponse {
  return {
    ...det,
    row: patchRowSinEvidenciasPendientes(det.row),
    ui_policy: det.ui_policy
      ? { ...det.ui_policy, solo_evidencias_pendientes: false }
      : det.ui_policy,
  };
}
