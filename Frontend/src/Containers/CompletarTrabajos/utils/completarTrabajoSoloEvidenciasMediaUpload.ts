import {
  runManualMediaSave,
  type ManualMediaSaveOutcome,
  type ManualMediaSaveResult,
} from "../../../features/media/utils/actuacionManualMediaSave";
import type { MediaQueuedFile, RutaItemArchivosListResponse } from "../../../features/media/mediaTypes";

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
};

/** Misma condición de éxito que Mis trabajos → Cargar más fotos. */
export async function runCompletarTrabajoSoloEvidenciasMediaUpload(
  deps: CompletarTrabajoSoloEvidenciasMediaUploadDeps
): Promise<ManualMediaSaveResult> {
  return runManualMediaSave({
    rutaItemId: deps.rutaItemId,
    uploadAll: deps.uploadAll,
    getQueueItems: deps.getQueueItems,
    applyQueueItems: deps.applyQueueItems,
    clearUploadedFromQueue: deps.clearUploadedFromQueue,
    reloadServer: deps.reloadServer,
    fetchArchivosForReconcile: deps.fetchArchivosForReconcile,
  });
}

export function shouldCloseCompletarTrabajoAfterSoloEvidenciasUpload(
  outcome: ManualMediaSaveOutcome
): boolean {
  return outcome === "success";
}
