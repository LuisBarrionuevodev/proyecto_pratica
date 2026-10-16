import type { ICompletarTrabajoDetalleResponse } from "../../../api/completarTrabajoApi";
import {
  runManualMediaSave,
  type ManualMediaSaveOutcome,
  type ManualMediaSaveResult,
} from "../../../features/media/utils/actuacionManualMediaSave";
import type { MediaQueuedFile, RutaItemArchivosListResponse } from "../../../features/media/mediaTypes";
import { isLocalCompletarTrabajoMediaQueueFinished } from "./completarTrabajoEvidenciasConfirm";
import {
  waitForCompletarTrabajoEvidenciasBackendSync,
  type WaitCompletarTrabajoEvidenciasSyncOptions,
} from "./completarTrabajoMediaPostUploadSync";

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
  /** Inyectable en tests (delays / mocks de reconsulta). */
  evidenciasSyncOptions?: WaitCompletarTrabajoEvidenciasSyncOptions;
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

  const localFinished = isLocalCompletarTrabajoMediaQueueFinished(deps.getQueueItems());
  if (!localFinished) {
    return base;
  }

  const sync = await waitForCompletarTrabajoEvidenciasBackendSync(deps.rutaItemId, {
    fetchDetalle: deps.fetchDetalleForConfirm,
    fetchArchivos: deps.fetchArchivosForReconcile,
    ...deps.evidenciasSyncOptions,
  });

  if (sync.status === "completo") {
    deps.clearUploadedFromQueue();
    return {
      outcome: "success",
      refreshFailed: base.refreshFailed,
    };
  }

  if (base.outcome === "success" || localFinished) {
    return {
      outcome: "partial",
      refreshFailed: base.refreshFailed || sync.status === "error",
    };
  }

  return base;
}

export function shouldCloseCompletarTrabajoAfterSoloEvidenciasUpload(
  outcome: ManualMediaSaveOutcome
): boolean {
  return outcome === "success";
}
