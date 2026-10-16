import { getCompletarTrabajoDetalle } from "../../../api/completarTrabajoApi";
import { getRutaItemArchivos } from "../../../api/mediaApi";
import type { MediaQueuedFile, RutaItemArchivosListResponse } from "../../../features/media/mediaTypes";
import {
  countUploadableQueueItems,
  isQueueStillUploadable,
} from "../../../features/media/utils/actuacionManualMediaSave";
import {
  classifyCompletarTrabajoDetalle,
  type CompletarTrabajoRecoveryStatus,
} from "./completarTrabajoPostErrorRecovery";

/**
 * Diagnóstico (MEDIA-UX.1B): falsos errores tras corte suelen venir de:
 * - `uploadQueuedFilesWithConcurrency` lanza tras `complete` fallido en red aunque el archivo quedó READY.
 * - Cola local en `error` con `archivoId` ya persistido (no reintento real).
 * - `getRutaItemArchivos` falla al refrescar: no implica subida incompleta.
 * Reconciliar con GET `/ruta-items/:id/archivos` antes de mostrar warning.
 */

export type CompletarTrabajoMediaUploadFinalizeStatus =
  | "success"
  | "partial"
  | "guardado_fotos_pendientes"
  | "no_guardado"
  | "unknown";

export type CompletarTrabajoMediaUploadFinalizeResult = {
  status: CompletarTrabajoMediaUploadFinalizeStatus;
  reconciledItems: MediaQueuedFile[];
  archivosRefreshFailed: boolean;
  detalleStatus?: CompletarTrabajoRecoveryStatus;
};

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

export type CompletarTrabajoMediaUploadFinalizeDeps = {
  rutaItemId: number;
  queueItems: MediaQueuedFile[];
  fetchArchivos?: (rutaItemId: number) => Promise<RutaItemArchivosListResponse>;
  fetchDetalle?: (rutaItemId: number) => Promise<Awaited<ReturnType<typeof getCompletarTrabajoDetalle>>>;
};

/**
 * Tras un intento de subida (éxito o excepción), decide el estado operativo real.
 */
export async function finalizeCompletarTrabajoMediaUploadAttempt(
  deps: CompletarTrabajoMediaUploadFinalizeDeps
): Promise<CompletarTrabajoMediaUploadFinalizeResult> {
  let reconciled = promoteQueueItemsWithPersistedArchivoId([...deps.queueItems]);
  let archivosRefreshFailed = false;

  if (!isQueueStillUploadable(reconciled)) {
    return { status: "success", reconciledItems: reconciled, archivosRefreshFailed: false };
  }

  const fetchArchivos = deps.fetchArchivos ?? getRutaItemArchivos;
  try {
    const server = await fetchArchivos(deps.rutaItemId);
    reconciled = reconcileQueueItemsWithServerArchivos(reconciled, server);
  } catch {
    archivosRefreshFailed = true;
  }

  if (!isQueueStillUploadable(reconciled)) {
    return {
      status: "success",
      reconciledItems: reconciled,
      archivosRefreshFailed,
    };
  }

  const fetchDetalle = deps.fetchDetalle ?? getCompletarTrabajoDetalle;
  try {
    const det = await fetchDetalle(deps.rutaItemId);
    const detalleStatus = classifyCompletarTrabajoDetalle(det);
    if (detalleStatus === "completo" && countUploadableQueueItems(reconciled) === 0) {
      return {
        status: "success",
        reconciledItems: reconciled,
        archivosRefreshFailed,
        detalleStatus,
      };
    }
    if (detalleStatus === "completo" && isQueueStillUploadable(reconciled)) {
      return {
        status: "success",
        reconciledItems: reconciled,
        archivosRefreshFailed,
        detalleStatus,
      };
    }
    if (detalleStatus === "guardado_fotos_pendientes") {
      return {
        status: "guardado_fotos_pendientes",
        reconciledItems: reconciled,
        archivosRefreshFailed,
        detalleStatus,
      };
    }
    if (detalleStatus === "no_guardado") {
      return {
        status: "no_guardado",
        reconciledItems: reconciled,
        archivosRefreshFailed,
        detalleStatus,
      };
    }
    return {
      status: "partial",
      reconciledItems: reconciled,
      archivosRefreshFailed,
      detalleStatus,
    };
  } catch {
    return {
      status: isQueueStillUploadable(reconciled) ? "unknown" : "success",
      reconciledItems: reconciled,
      archivosRefreshFailed,
    };
  }
}
