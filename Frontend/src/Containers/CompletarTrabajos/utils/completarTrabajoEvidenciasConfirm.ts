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

export type FetchDetalleConfirmaSinEvidenciasResult =
  | { status: "completo" }
  | { status: "pendiente" }
  | { status: "error" };

/**
 * Reconsulta detalle tras carga de fotos. Un fallo HTTP no implica “fotos pendientes”.
 */
export async function fetchDetalleConfirmaSinEvidenciasPendientesDetailed(
  rutaItemId: number,
  fetchDetalle: (id: number) => Promise<ICompletarTrabajoDetalleResponse> = getCompletarTrabajoDetalle
): Promise<FetchDetalleConfirmaSinEvidenciasResult> {
  try {
    const det = await fetchDetalle(rutaItemId);
    return detalleConfirmaCompletarTrabajoSinEvidenciasPendientes(det)
      ? { status: "completo" }
      : { status: "pendiente" };
  } catch {
    return { status: "error" };
  }
}

export async function fetchDetalleConfirmaSinEvidenciasPendientes(
  rutaItemId: number,
  fetchDetalle: (id: number) => Promise<ICompletarTrabajoDetalleResponse> = getCompletarTrabajoDetalle
): Promise<boolean> {
  const result = await fetchDetalleConfirmaSinEvidenciasPendientesDetailed(rutaItemId, fetchDetalle);
  return result.status === "completo";
}

/** Cola local finalizada (todo READY o sin pendientes reales de subida). */
export function isLocalCompletarTrabajoMediaQueueFinished(items: MediaQueuedFile[]): boolean {
  if (items.length === 0) return true;
  if (countUploadableQueueItems(items) > 0) return false;
  return !hasIncompleteUploadInQueue(items);
}
