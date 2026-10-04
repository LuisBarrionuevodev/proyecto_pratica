import { postMediaComplete, postMediaUploadIntent, type UploadIntentBody } from "../../api/mediaApi";
import { sha256HexFromFile } from "./sha256File";
import type { MediaQueuedFile } from "./mediaTypes";

export type XhrUploadProgress = {
  loaded: number;
  total: number;
};

/**
 * Sube un archivo al bucket con URL firmada (PUT) reportando progreso vía XHR.
 */
export function putFileToPresignedUrl(
  uploadUrl: string,
  file: File,
  contentType: string,
  onProgress?: (p: XhrUploadProgress) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", uploadUrl, true);
    xhr.setRequestHeader("Content-Type", contentType);
    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable && onProgress) {
        onProgress({ loaded: ev.loaded, total: ev.total });
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Error de subida (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error("Error de red al subir el archivo."));
    xhr.send(file);
  });
}

export type UploadSingleResult = { archivoId: number };

/**
 * Flujo intent → PUT → complete para un archivo local.
 */
export async function uploadSingleQueuedFile(
  rutaItemId: number,
  item: MediaQueuedFile,
  onProgress?: (pct: number) => void
): Promise<UploadSingleResult> {
  const contentType = (item.file.type || "application/octet-stream").toLowerCase();
  const sha256 = await sha256HexFromFile(item.file);
  const body: UploadIntentBody = {
    categoria: item.categoria,
    filename: item.file.name,
    content_type: contentType,
    byte_size: item.file.size,
    sha256,
  };
  const intent = await postMediaUploadIntent(rutaItemId, body);
  await putFileToPresignedUrl(intent.upload_url, item.file, contentType, (p) => {
    if (p.total > 0 && onProgress) {
      onProgress(Math.min(100, Math.round((p.loaded / p.total) * 100)));
    }
  });
  await postMediaComplete(intent.archivo_id);
  return { archivoId: intent.archivo_id };
}

const DEFAULT_CONCURRENCY = 2;

/**
 * Sube archivos pendientes o en error (no re-sube READY).
 */
export async function uploadQueuedFilesWithConcurrency(
  rutaItemId: number,
  items: MediaQueuedFile[],
  options: {
    concurrency?: number;
    onItemPhase?: (
      localId: string,
      phase: MediaQueuedFile["phase"],
      progressPct?: number,
      meta?: { errorMessage?: string | null; archivoId?: number | null }
    ) => void;
    onGlobalProgress?: (pct: number) => void;
  }
): Promise<void> {
  const toUpload = items.filter((x) => x.phase === "pending" || (x.phase === "error" && !x.archivoId));
  if (toUpload.length === 0) return;
  const totalBytes = toUpload.reduce((s, f) => s + f.file.size, 0);
  let uploadedBytes = 0;
  const concurrency = options.concurrency ?? DEFAULT_CONCURRENCY;
  let index = 0;

  const failedIds: string[] = [];

  const runOne = async (item: MediaQueuedFile) => {
    options.onItemPhase?.(item.localId, "preparing", 0);
    try {
      options.onItemPhase?.(item.localId, "uploading", 0);
      const result = await uploadSingleQueuedFile(rutaItemId, item, (pct) => {
        options.onItemPhase?.(item.localId, "uploading", pct);
      });
      options.onItemPhase?.(item.localId, "verifying", 100);
      item.archivoId = result.archivoId;
      options.onItemPhase?.(item.localId, "ready", 100, { archivoId: result.archivoId });
      uploadedBytes += item.file.size;
      if (options.onGlobalProgress && totalBytes > 0) {
        options.onGlobalProgress(Math.min(100, Math.round((uploadedBytes / totalBytes) * 100)));
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error al subir el archivo.";
      options.onItemPhase?.(item.localId, "error", 0, { errorMessage: msg });
      failedIds.push(item.localId);
      item.errorMessage = msg;
    }
  };

  const workers = Array.from({ length: Math.min(concurrency, toUpload.length) }, async () => {
    while (index < toUpload.length) {
      const current = toUpload[index++];
      await runOne(current);
    }
  });
  await Promise.all(workers);
  if (failedIds.length > 0) {
    throw new Error("Uno o más archivos no pudieron subirse.");
  }
}
