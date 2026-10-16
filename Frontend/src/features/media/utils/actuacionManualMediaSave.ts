import type { MediaQueuedFile, RutaItemArchivosListResponse } from "../mediaTypes";
import { reconcileMediaQueueAfterUploadAttempt } from "./mediaUploadQueueReconcile";

export type ManualMediaSaveOutcome = "success" | "partial" | "empty";

export function countUploadableQueueItems(items: MediaQueuedFile[]): number {
  return items.filter(
    (x) => x.phase === "pending" || (x.phase === "error" && x.archivoId == null)
  ).length;
}

/** True si quedó algún archivo que aún requiere subida o reintento real. */
export function hasIncompleteUploadInQueue(items: MediaQueuedFile[]): boolean {
  if (countUploadableQueueItems(items) > 0) return true;
  return items.some(
    (x) => x.phase === "preparing" || x.phase === "uploading" || x.phase === "verifying"
  );
}

/** Tras `uploadAll`, indica si la cola sigue con pendientes reales (ignora READY y error con archivoId). */
export function isQueueStillUploadable(items: MediaQueuedFile[]): boolean {
  return hasIncompleteUploadInQueue(items);
}

export type ManualMediaSaveResult = {
  outcome: ManualMediaSaveOutcome;
  refreshFailed: boolean;
};

/**
 * Guardado manual Mis trabajos: sube cola, limpia READY local y refresca servidor.
 * El refresh fallido no convierte un upload exitoso en `partial`.
 */
export async function runManualMediaSave(params: {
  rutaItemId: number;
  uploadAll: (rutaItemId: number) => Promise<void>;
  getQueueItems: () => MediaQueuedFile[];
  /** Sincroniza la cola local tras reconciliar con el servidor (Completar trabajo). */
  applyQueueItems?: (items: MediaQueuedFile[]) => void;
  clearUploadedFromQueue: () => void;
  reloadServer: () => Promise<void>;
  fetchArchivosForReconcile?: (rutaItemId: number) => Promise<RutaItemArchivosListResponse>;
}): Promise<ManualMediaSaveResult> {
  if (countUploadableQueueItems(params.getQueueItems()) === 0) {
    return { outcome: "empty", refreshFailed: false };
  }

  try {
    await params.uploadAll(params.rutaItemId);
  } catch {
    // Puede haber archivos READY en servidor pese al error agregado del pipeline.
  }

  const reconciled = await reconcileMediaQueueAfterUploadAttempt(
    params.rutaItemId,
    params.getQueueItems(),
    params.fetchArchivosForReconcile
  );
  params.applyQueueItems?.(reconciled.items);

  if (hasIncompleteUploadInQueue(reconciled.items)) {
    return { outcome: "partial", refreshFailed: reconciled.archivosRefreshFailed };
  }

  params.clearUploadedFromQueue();

  let refreshFailed = reconciled.archivosRefreshFailed;
  try {
    await params.reloadServer();
  } catch {
    refreshFailed = true;
  }
  return { outcome: "success", refreshFailed };
}

/** Cierra el modal de fotos Inspector solo tras éxito operativo de subida. */
export function shouldCloseInspectorFotosModalAfterSave(outcome: ManualMediaSaveOutcome): boolean {
  return outcome === "success";
}

/** Etiqueta del botón principal en Mis trabajos / continuación de carga. */
export function manualMediaSavePrimaryLabel(
  uploadableCount: number,
  hasRetryable: boolean
): string {
  if (uploadableCount <= 0) return "GUARDAR FOTOS";
  return hasRetryable ? "CONTINUAR SUBIDA" : "GUARDAR FOTOS";
}

export const MANUAL_MEDIA_PARTIAL_MESSAGE =
  "Algunas fotos no terminaron de subir. Las que ya quedaron guardadas se mantienen; tocá CONTINUAR SUBIDA para reintentar solo las faltantes.";

export const MANUAL_MEDIA_RELOAD_HINT =
  "Las fotos ya guardadas se muestran abajo. Volvé a seleccionar únicamente las que no terminaron de subir.";

export const MANUAL_MEDIA_GALLERY_REFRESH_HINT =
  "Fotos cargadas correctamente. La galería se actualizará al volver a abrirla.";
