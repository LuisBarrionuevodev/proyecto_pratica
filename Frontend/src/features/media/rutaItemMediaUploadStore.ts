import {
  MEDIA_CATEGORIA_FOTO_ACTA,
  MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
  MEDIA_CATEGORIA_FOTO_INSPECCION,
  type MediaCategoria,
} from "./mediaConstants";
import { validateLocalMediaFile } from "./mediaFileValidation";
import type { MediaQueuedFile } from "./mediaTypes";
import { uploadQueuedFilesWithConcurrency } from "./mediaUploadPipeline";
import {
  sliceFilesToAvailableQuota,
  type MediaQuotaAddResult,
} from "../../Containers/CompletarTrabajos/utils/completarTrabajoMediaQuota";
export type RutaItemMediaUploadSessionState = {
  active: boolean;
  globalPct: number;
  items: MediaQueuedFile[];
};

function newLocalId(): string {
  return `mq-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function previewForFile(file: File): string | null {
  try {
    const ct = (file.type || "").toLowerCase();
    if (ct.startsWith("image/")) {
      return URL.createObjectURL(file);
    }
  } catch {
    return null;
  }
  return null;
}

const INITIAL_SESSION: RutaItemMediaUploadSessionState = {
  active: false,
  globalPct: 0,
  items: [],
};

type RutaItemUploadBucket = {
  items: MediaQueuedFile[];
  session: RutaItemMediaUploadSessionState;
  uploadEpoch: number;
  abortController: AbortController | null;
};

const buckets = new Map<number, RutaItemUploadBucket>();
const listeners = new Set<() => void>();

function emitChange(): void {
  listeners.forEach((l) => l());
}

function getBucket(rutaItemId: number): RutaItemUploadBucket {
  let b = buckets.get(rutaItemId);
  if (!b) {
    b = {
      items: [],
      session: { ...INITIAL_SESSION },
      uploadEpoch: 0,
      abortController: null,
    };
    buckets.set(rutaItemId, b);
  }
  return b;
}

export function subscribeRutaItemMediaUploadStore(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export type RutaItemMediaUploadSnapshot = {
  items: MediaQueuedFile[];
  session: RutaItemMediaUploadSessionState;
  hasPendingUpload: boolean;
  hasRetryableUpload: boolean;
  retryableCount: number;
  uploadableCount: number;
};

const EMPTY_SNAPSHOT: RutaItemMediaUploadSnapshot = {
  items: [],
  session: INITIAL_SESSION,
  hasPendingUpload: false,
  hasRetryableUpload: false,
  retryableCount: 0,
  uploadableCount: 0,
};

function computeFlags(items: MediaQueuedFile[]) {
  const hasPendingUpload = items.some(
    (x) => x.phase === "pending" || (x.phase === "error" && x.archivoId == null)
  );
  const hasRetryableUpload = items.some(
    (x) =>
      x.phase !== "ready" &&
      (x.phase === "pending" || x.phase === "error")
  );
  const retryableCount = items.filter(
    (x) => x.phase === "pending" || x.phase === "error"
  ).length;
  const uploadableCount = retryableCount;
  return { hasPendingUpload, hasRetryableUpload, retryableCount, uploadableCount };
}

export function getRutaItemMediaUploadSnapshot(
  rutaItemId: number | null | undefined
): RutaItemMediaUploadSnapshot {
  if (rutaItemId == null) return EMPTY_SNAPSHOT;
  const b = buckets.get(rutaItemId);
  if (!b) return EMPTY_SNAPSHOT;
  const flags = computeFlags(b.items);
  return {
    items: b.items ?? [],
    session: b.session ?? INITIAL_SESSION,
    hasPendingUpload: flags.hasPendingUpload,
    hasRetryableUpload: flags.hasRetryableUpload,
    retryableCount: flags.retryableCount,
    uploadableCount: flags.uploadableCount,
  };
}

export function cancelUploadForRutaItem(rutaItemId: number): void {
  const b = buckets.get(rutaItemId);
  if (!b) return;
  b.abortController?.abort();
  b.abortController = null;
  b.uploadEpoch += 1;
  b.session = { ...b.session, active: false };
  emitChange();
}

export function clearRutaItemMediaUploadState(rutaItemId: number): void {
  cancelUploadForRutaItem(rutaItemId);
  const b = buckets.get(rutaItemId);
  if (!b) return;
  b.items.forEach((x) => {
    if (x.previewUrl) URL.revokeObjectURL(x.previewUrl);
  });
  buckets.delete(rutaItemId);
  emitChange();
}

function patchItemInBucket(
  rutaItemId: number,
  localId: string,
  patch: Partial<MediaQueuedFile>
): void {
  const b = getBucket(rutaItemId);
  b.items = b.items.map((x) => (x.localId === localId ? { ...x, ...patch } : x));
  if (b.session.active) {
    b.session = {
      ...b.session,
      items: b.session.items.map((x) => (x.localId === localId ? { ...x, ...patch } : x)),
    };
  }
  emitChange();
}

export function addFilesForRutaItem(
  rutaItemId: number,
  categoria: MediaCategoria,
  files: FileList | File[],
  serverCount = 0
): MediaQuotaAddResult {
  try {
    const b = getBucket(rutaItemId);
    const list = Array.from(files);
    const quota = sliceFilesToAvailableQuota(list, categoria, serverCount, b.items);
    let addedCount = 0;
    const next = [...b.items];
    let slotCount =
      serverCount + next.filter((x) => x.categoria === categoria && x.phase !== "error").length;
    for (const file of quota.accepted) {
      const err = validateLocalMediaFile(file, categoria, slotCount);
      if (err) continue;
      next.push({
        localId: newLocalId(),
        file,
        categoria,
        tipoDocumento: null,
        phase: "pending",
        progressPct: 0,
        errorMessage: null,
        archivoId: null,
        previewUrl: previewForFile(file),
      });
      slotCount += 1;
      addedCount += 1;
    }
    b.items = next;
    emitChange();
    return {
      accepted: quota.accepted.slice(0, addedCount),
      added: addedCount,
      skipped: list.length - addedCount,
      quotaFull: list.length > addedCount && addedCount > 0,
    };
  } catch {
    return { accepted: [], added: 0, skipped: Array.from(files).length, quotaFull: false };
  }
}

export function removeItemForRutaItem(rutaItemId: number, localId: string): void {
  const b = getBucket(rutaItemId);
  const target = b.items.find((x) => x.localId === localId);
  if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
  b.items = b.items.filter((x) => x.localId !== localId);
  if (b.session.active) {
    b.session = {
      ...b.session,
      items: b.session.items.filter((x) => x.localId !== localId),
    };
  }
  emitChange();
}

export function retryAllRetryableForRutaItem(rutaItemId: number): void {
  const b = getBucket(rutaItemId);
  b.items = b.items.map((x) =>
    x.phase === "ready"
      ? x
      : x.phase === "error" || x.phase === "pending"
        ? {
            ...x,
            phase: "pending" as const,
            progressPct: 0,
            errorMessage: null,
          }
        : x
  );
  emitChange();
}

export async function uploadAllForRutaItem(
  rutaItemId: number,
  concurrency = 1
): Promise<void> {
  const b = getBucket(rutaItemId);
  b.abortController?.abort();
  const controller = new AbortController();
  b.abortController = controller;
  const epochAtStart = ++b.uploadEpoch;

  const current = [...b.items];
  const snapshot = current.filter(
    (x) => x.phase === "pending" || x.phase === "error"
  );
  if (snapshot.length === 0) return;

  b.session = { active: true, globalPct: 0, items: [...current] };
  emitChange();

  const isStale = () => {
    const live = buckets.get(rutaItemId);
    return !live || live.uploadEpoch !== epochAtStart;
  };

  try {
    await uploadQueuedFilesWithConcurrency(rutaItemId, current, {
      concurrency,
      abortSignal: controller.signal,
      isStale,
      onItemPhase: (localId, phase, progressPct, meta) => {
        if (isStale()) return;
        patchItemInBucket(rutaItemId, localId, {
          phase,
          progressPct: progressPct ?? 0,
          ...(meta?.archivoId != null ? { archivoId: meta.archivoId } : {}),
          ...(phase === "error"
            ? {
                errorMessage: meta?.errorMessage ?? "Error al subir",
                ...(meta?.archivoId != null ? { archivoId: meta.archivoId } : {}),
              }
            : { errorMessage: null }),
        });
      },
      onGlobalProgress: (pct) => {
        if (isStale()) return;
        const live = getBucket(rutaItemId);
        live.session = { ...live.session, globalPct: pct };
        emitChange();
      },
    });
  } finally {
    if (!isStale()) {
      const live = getBucket(rutaItemId);
      live.session = { ...live.session, active: false };
      live.abortController = null;
      emitChange();
    }
  }
}

/** Solo tests: vacía el mapa de sesión. */
export function __resetRutaItemMediaUploadStoreForTests(): void {
  for (const [id] of buckets) {
    clearRutaItemMediaUploadState(id);
  }
}

export const COMPLETAR_TRABAJO_MEDIA_CATEGORIAS = [
  MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
  MEDIA_CATEGORIA_FOTO_ACTA,
  MEDIA_CATEGORIA_FOTO_INSPECCION,
] as const;
