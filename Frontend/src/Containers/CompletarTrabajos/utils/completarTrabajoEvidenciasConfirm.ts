import {
  getCompletarTrabajoDetalle,
  type ICompletarTrabajoDetalleResponse,
} from "../../../api/completarTrabajoApi";
import type { MediaQueuedFile } from "../../../features/media/mediaTypes";
import {
  countUploadableQueueItems,
  hasIncompleteUploadInQueue,
} from "../../../features/media/utils/actuacionManualMediaSave";
import { classifyCompletarTrabajoDetalle } from "./completarTrabajoPostErrorRecovery";

/** El backend no reporta evidencias pendientes del flujo Completar trabajo. */
export function detalleConfirmaCompletarTrabajoSinEvidenciasPendientes(
  det: ICompletarTrabajoDetalleResponse
): boolean {
  return classifyCompletarTrabajoDetalle(det) === "completo";
}

export async function fetchDetalleConfirmaSinEvidenciasPendientes(
  rutaItemId: number,
  fetchDetalle: (id: number) => Promise<ICompletarTrabajoDetalleResponse> = getCompletarTrabajoDetalle
): Promise<boolean> {
  try {
    const det = await fetchDetalle(rutaItemId);
    return detalleConfirmaCompletarTrabajoSinEvidenciasPendientes(det);
  } catch {
    return false;
  }
}

/** Cola local finalizada (todo READY o sin pendientes reales de subida). */
export function isLocalCompletarTrabajoMediaQueueFinished(items: MediaQueuedFile[]): boolean {
  if (items.length === 0) return true;
  if (countUploadableQueueItems(items) > 0) return false;
  return !hasIncompleteUploadInQueue(items);
}
