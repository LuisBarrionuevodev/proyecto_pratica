import { postMediaComplete, postMediaUploadIntent, type UploadIntentBody } from "../../api/mediaApi";
import { mediaErrorMessageFromUnknown } from "./mediaApiErrors";
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
  onProgress?: (p: XhrUploadProgress) => void,
  abortSignal?: AbortSignal
): Promise<void> {
  return new Promise((resolve, reject) => {
    if (abortSignal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const xhr = new XMLHttpRequest();
    const onAbort = () => {
      xhr.abort();
      reject(new DOMException("Aborted", "AbortError"));
    };
    abortSignal?.addEventListener("abort", onAbort, { once: true });
    xhr.open("PUT", uploadUrl, true);
    xhr.setRequestHeader("Content-Type", contentType);
    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable && onProgress) {
        onProgress({ loaded: ev.loaded, total: ev.total });
      }
    };
    xhr.onload = () => {
      abortSignal?.removeEventListener("abort", onAbort);
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Error de subida (${xhr.status})`));
    };
    xhr.onerror = () => {
      abortSignal?.removeEventListener("abort", onAbort);
      reject(new Error("Error de red al subir el archivo."));
    };
    xhr.onabort = () => {
      abortSignal?.removeEventListener("abort", onAbort);
      reject(new DOMException("Aborted", "AbortError"));
    };
    xhr.send(file);
  });
}

export type UploadSingleResult = { archivoId: number };

/**
 * Flujo intent → PUT → complete para un archivo local (idempotente por SHA en servidor).
 */
export async function uploadSingleQueuedFile(
  rutaItemId: number,
  item: MediaQueuedFile,
  onProgress?: (pct: number) => void,
  abortSignal?: AbortSignal
): Promise<UploadSingleResult> {
  if (abortSignal?.aborted) {
    throw new DOMException("Aborted", "AbortError");
  }
  if (item.phase === "ready" && item.archivoId != null) {
    return { archivoId: item.archivoId };
  }
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
  const archivoId = intent.archivo_id;
  if (intent.status === "READY") {
    return { archivoId };
  }
  if (!intent.upload_url) {
    throw new Error("No se recibió URL de subida.");
  }
  await putFileToPresignedUrl(
    intent.upload_url,
    item.file,
    contentType,
    (p) => {
      if (p.total > 0 && onProgress) {
        onProgress(Math.min(100, Math.round((p.loaded / p.total) * 100)));
      }
    },
    abortSignal
  );
  await postMediaComplete(archivoId);
  return { archivoId };
}

export const MOBILE_UPLOAD_CONCURRENCY = 1;

/**
 * Sube archivos pendientes o en error (no re-sube READY).
 */
export async function uploadQueuedFilesWithConcurrency(
  rutaItemId: number,
  items: MediaQueuedFile[],
  options: {
    concurrency?: number;
    abortSignal?: AbortSignal;
    isStale?: () => boolean;
    onItemPhase?: (
      localId: string,
      phase: MediaQueuedFile["phase"],
      progressPct?: number,
      meta?: { errorMessage?: string | null; archivoId?: number | null }
    ) => void;
    onGlobalProgress?: (pct: number) => void;
  }
): Promise<void> {
  const toUpload = items.filter(
    (x) =>
      x.phase !== "ready" &&
      (x.phase === "pending" || (x.phase === "error" && x.archivoId != null) || (x.phase === "error" && !x.archivoId))
  );
  if (toUpload.length === 0) return;
  const totalBytes = toUpload.reduce((s, f) => s + f.file.size, 0);
  const bytesLoadedById = new Map<string, number>();
  const emitGlobalBytes = () => {
    if (!options.onGlobalProgress || totalBytes <= 0) return;
    let sum = 0;
    for (const f of toUpload) {
      sum += bytesLoadedById.get(f.localId) ?? 0;
    }
    options.onGlobalProgress(Math.min(100, Math.round((sum / totalBytes) * 100)));
  };
  const concurrency = options.concurrency ?? MOBILE_UPLOAD_CONCURRENCY;
  let index = 0;

  const failedIds: string[] = [];

  const runOne = async (item: MediaQueuedFile) => {
    if (options.isStale?.()) return;
    if (item.phase === "ready") return;
    options.onItemPhase?.(item.localId, "preparing", 0);
    let archivoId: number | null = item.archivoId;
    try {
      if (options.isStale?.()) return;
      options.onItemPhase?.(item.localId, "uploading", 0, { archivoId });
      bytesLoadedById.set(item.localId, 0);
      const result = await uploadSingleQueuedFile(
        rutaItemId,
        item,
        (pct) => {
          if (options.isStale?.()) return;
          options.onItemPhase?.(item.localId, "uploading", pct, {
            archivoId: archivoId ?? undefined,
          });
          bytesLoadedById.set(item.localId, Math.round((pct / 100) * item.file.size));
          emitGlobalBytes();
        },
        options.abortSignal
      );
      archivoId = result.archivoId;
      options.onItemPhase?.(item.localId, "verifying", 100, { archivoId });
      bytesLoadedById.set(item.localId, item.file.size);
      emitGlobalBytes();
      options.onItemPhase?.(item.localId, "ready", 100, { archivoId });
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        return;
      }
      if (options.isStale?.()) return;
      const msg = mediaErrorMessageFromUnknown(e);
      options.onItemPhase?.(item.localId, "error", 0, {
        errorMessage: msg,
        archivoId: archivoId ?? item.archivoId,
      });
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
  if (options.isStale?.()) return;
  if (options.abortSignal?.aborted) return;
  if (failedIds.length > 0) {
    throw new Error("Uno o más archivos no pudieron subirse.");
  }
}
