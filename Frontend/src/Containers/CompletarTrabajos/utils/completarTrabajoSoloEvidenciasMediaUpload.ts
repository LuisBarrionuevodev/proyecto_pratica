import type { ICompletarTrabajoDetalleResponse } from "../../../api/completarTrabajoApi";
import {
  runManualMediaSave,
  type ManualMediaSaveOutcome,
  type ManualMediaSaveResult,
} from "../../../features/media/utils/actuacionManualMediaSave";
import type { MediaQueuedFile, RutaItemArchivosListResponse } from "../../../features/media/mediaTypes";
import {
  fetchDetalleConfirmaSinEvidenciasPendientes,
  isLocalCompletarTrabajoMediaQueueFinished,
} from "./completarTrabajoEvidenciasConfirm";

export const COMPLETAR_TRABAJO_FOTOS_SUCCESS_MESSAGE =
  "Trabajo y fotos subidos correctamente.";

export type CompletarTrabajoSoloEvidenciasMediaUploadDeps = {
  rutaItemId: number;
  uploadAll: (rutaItemId: number) => Promise<void>;
  getQueueItems: () => MediaQueuedFile[];
  applyQueueItems: (items: MediaQueuedFile[]) => void;
  clearUploadedFromQueue: () => void;
  reloadServer: () => Promise<void>;
  fetchArchivosForReconcile?: (rutaItemId: number) => Promise<RutaItemArchivosListResponse>;
  fetchDetalleForConfirm?: (rutaItemId: number) => Promise<ICompletarTrabajoDetalleResponse>;
};

/**
 * Mis trabajos + confirmación backend: éxito definitivo solo si la cola terminó y el detalle no reporta pendientes.
 */
export async function runCompletarTrabajoSoloEvidenciasMediaUpload(
  deps: CompletarTrabajoSoloEvidenciasMediaUploadDeps
): Promise<ManualMediaSaveResult> {
  const base = await runManualMediaSave({
    rutaItemId: deps.rutaItemId,
    uploadAll: deps.uploadAll,
    getQueueItems: deps.getQueueItems,
    applyQueueItems: deps.applyQueueItems,
    clearUploadedFromQueue: deps.clearUploadedFromQueue,
    reloadServer: deps.reloadServer,
    fetchArchivosForReconcile: deps.fetchArchivosForReconcile,
  });

  const backendOk = await fetchDetalleConfirmaSinEvidenciasPendientes(
    deps.rutaItemId,
    deps.fetchDetalleForConfirm
  );
  const localFinished = isLocalCompletarTrabajoMediaQueueFinished(deps.getQueueItems());

  if (base.outcome === "success" && backendOk) {
    return base;
  }

  if (localFinished && backendOk) {
    deps.clearUploadedFromQueue();
    return {
      outcome: "success",
      refreshFailed: base.refreshFailed,
    };
  }

  if (base.outcome === "success" && !backendOk) {
    return { outcome: "partial", refreshFailed: base.refreshFailed };
  }

  return base;
}

export function shouldCloseCompletarTrabajoAfterSoloEvidenciasUpload(
  outcome: ManualMediaSaveOutcome
): boolean {
  return outcome === "success";
}
