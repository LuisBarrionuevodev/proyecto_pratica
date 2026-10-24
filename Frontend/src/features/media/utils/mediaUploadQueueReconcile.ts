import { getRutaItemArchivos } from "../../../api/mediaApi";
import type { MediaQueuedFile, RutaItemArchivosListResponse } from "../mediaTypes";
import { hasIncompleteUploadInQueue } from "./actuacionManualMediaSave";

function allArchivoIdsOnServer(
  archivoId: number,
  server: RutaItemArchivosListResponse
): boolean {
  const ids = [
    ...server.foto_acta,
    ...server.foto_documentacion_local,
    ...server.foto_inspeccion,
  ];
  return ids.some((a) => a.archivo_id === archivoId);
}

/** Error local con archivoId: puede estar READY en servidor tras fallo de red tardío. */
export function queueNeedsServerReconciliation(items: MediaQueuedFile[]): boolean {
  return items.some((x) => x.phase === "error" && x.archivoId != null);
}

/** Alinea fases locales con archivos ya listados en el servidor (READY implícito en listado). */
export function reconcileQueueItemsWithServerArchivos(
  items: MediaQueuedFile[],
  server: RutaItemArchivosListResponse
): MediaQueuedFile[] {
  return items.map((item) => {
    if (item.phase === "ready") return item;
    if (item.archivoId != null && allArchivoIdsOnServer(item.archivoId, server)) {
      return {
        ...item,
        phase: "ready",
        progressPct: 100,
        errorMessage: null,
      };
    }
    return item;
  });
}

/**
 * Tras un intento de subida (con o sin excepción), alinea la cola con el listado del servidor.
 * No reconcilia si `isCancelled` (uploadEpoch / cancelación deliberada).
 */
export async function reconcileMediaQueueAfterUploadAttempt(
  rutaItemId: number,
  items: MediaQueuedFile[],
  fetchArchivos?: (id: number) => Promise<RutaItemArchivosListResponse>,
  options?: { isCancelled?: () => boolean }
): Promise<{ items: MediaQueuedFile[]; archivosRefreshFailed: boolean }> {
  if (options?.isCancelled?.()) {
    return { items: [...items], archivosRefreshFailed: false };
  }

  const loadArchivos = fetchArchivos ?? getRutaItemArchivos;
  const shouldFetch =
    hasIncompleteUploadInQueue(items) || queueNeedsServerReconciliation(items);
  if (!shouldFetch) {
    return { items: [...items], archivosRefreshFailed: false };
  }

  try {
    const server = await loadArchivos(rutaItemId);
    if (options?.isCancelled?.()) {
      return { items: [...items], archivosRefreshFailed: false };
    }
    const reconciled = reconcileQueueItemsWithServerArchivos([...items], server);
    return { items: reconciled, archivosRefreshFailed: false };
  } catch {
    return { items: [...items], archivosRefreshFailed: true };
  }
}
