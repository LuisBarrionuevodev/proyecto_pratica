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

/** Error local con `archivoId` ya persistido → READY para UI y criterios de éxito. */
export function promoteQueueItemsWithPersistedArchivoId(
  items: MediaQueuedFile[]
): MediaQueuedFile[] {
  return items.map((item) => {
    if (item.archivoId != null && item.phase === "error") {
      return { ...item, phase: "ready", progressPct: 100, errorMessage: null };
    }
    return item;
  });
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
 */
export async function reconcileMediaQueueAfterUploadAttempt(
  rutaItemId: number,
  items: MediaQueuedFile[],
  fetchArchivos?: (id: number) => Promise<RutaItemArchivosListResponse>
): Promise<{ items: MediaQueuedFile[]; archivosRefreshFailed: boolean }> {
  const loadArchivos = fetchArchivos ?? getRutaItemArchivos;
  let reconciled = promoteQueueItemsWithPersistedArchivoId([...items]);
  if (!hasIncompleteUploadInQueue(reconciled)) {
    return { items: reconciled, archivosRefreshFailed: false };
  }
  try {
    const server = await loadArchivos(rutaItemId);
    reconciled = reconcileQueueItemsWithServerArchivos(reconciled, server);
    return { items: reconciled, archivosRefreshFailed: false };
  } catch {
    return { items: reconciled, archivosRefreshFailed: true };
  }
}
