import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import {
  MEDIA_CATEGORIA_FOTO_ACTA,
  MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
  MEDIA_CATEGORIA_FOTO_INSPECCION,
  type MediaCategoria,
} from "../mediaConstants";
import { validateLocalMediaFile } from "../mediaFileValidation";
import {
  MEDIA_UPLOAD_ORIGIN_COMPLETAR_TRABAJO,
  type MediaUploadOrigin,
} from "../mediaUploadOrigin";
import type { MediaQueuedFile } from "../mediaTypes";
import { uploadQueuedFilesWithConcurrency } from "../mediaUploadPipeline";
import { mergeMediaQueueItemPatch } from "../utils/mediaQueueItemPatch";
import { reconcileMediaQueueAfterUploadAttempt } from "../utils/mediaUploadQueueReconcile";
import { notifyMediaUploadSessionSettled } from "../utils/mediaUploadSessionNotify";
import { sliceFilesToAvailableQuota, type MediaQuotaAddResult } from "../../../Containers/CompletarTrabajos/utils/completarTrabajoMediaQuota";
import {
  addFilesForRutaItem,
  cancelUploadForRutaItem,
  clearRutaItemMediaUploadState,
  getRutaItemMediaUploadSnapshot,
  removeItemForRutaItem,
  retryAllRetryableForRutaItem,
  subscribeRutaItemMediaUploadStore,
  clearReadyFromQueueForRutaItem,
  replaceQueueItemsForRutaItem,
  uploadAllForRutaItem,
} from "../rutaItemMediaUploadStore";

function newLocalId(): string {
  return `mq-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function previewForFile(file: File): string | null {
  const ct = (file.type || "").toLowerCase();
  if (ct.startsWith("image/")) {
    return URL.createObjectURL(file);
  }
  return null;
}

export type MediaUploadSessionState = {
  active: boolean;
  globalPct: number;
  items: MediaQueuedFile[];
};

const INITIAL_SESSION: MediaUploadSessionState = {
  active: false,
  globalPct: 0,
  items: [],
};

/**
 * Cola y sesión de carga unificada para varias categorías (Media.1A / futuro 1B).
 */
export function useMediaUploadCoordinator(
  uploadOrigin: MediaUploadOrigin = MEDIA_UPLOAD_ORIGIN_COMPLETAR_TRABAJO
) {
  const [items, setItems] = useState<MediaQueuedFile[]>([]);
  const itemsRef = useRef<MediaQueuedFile[]>([]);
  const [session, setSession] = useState<MediaUploadSessionState>(INITIAL_SESSION);
  const uploadGenerationRef = useRef(0);

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  const getItems = useCallback(
    (categoria: MediaCategoria) => items.filter((x) => x.categoria === categoria),
    [items]
  );

  const patchItem = useCallback((localId: string, patch: Partial<MediaQueuedFile>) => {
    const next = itemsRef.current.map((x) =>
      x.localId === localId ? mergeMediaQueueItemPatch(x, patch) : x
    );
    itemsRef.current = next;
    setItems(next);
    setSession((prev) =>
      prev.active
        ? {
            ...prev,
            items: prev.items.map((x) =>
              x.localId === localId ? mergeMediaQueueItemPatch(x, patch) : x
            ),
          }
        : prev
    );
  }, []);

  const addFiles = useCallback(
    (
      categoria: MediaCategoria,
      files: FileList | File[],
      serverCount = 0
    ): MediaQuotaAddResult => {
      const list = Array.from(files);
      const quota = sliceFilesToAvailableQuota(
        list,
        categoria,
        serverCount,
        itemsRef.current
      );
      let addedCount = 0;
      setItems((prev) => {
        const next = [...prev];
        let slotCount =
          serverCount +
          next.filter((x) => x.categoria === categoria && x.phase !== "error").length;
        for (const file of quota.accepted) {
          const err = validateLocalMediaFile(file, categoria, slotCount);
          if (err) {
            continue;
          }
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
            uploadOrigin,
          });
          slotCount += 1;
          addedCount += 1;
        }
        itemsRef.current = next;
        return next;
      });
      return {
        accepted: quota.accepted.slice(0, addedCount),
        added: addedCount,
        skipped: list.length - addedCount,
        quotaFull: list.length > addedCount && addedCount > 0,
      };
    },
    [uploadOrigin]
  );

  const removeItem = useCallback((localId: string) => {
    setItems((prev) => {
      const target = prev.find((x) => x.localId === localId);
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
      const next = prev.filter((x) => x.localId !== localId);
      itemsRef.current = next;
      return next;
    });
  }, []);

  const retryItem = useCallback((localId: string) => {
    setItems((prev) => {
      const next: MediaQueuedFile[] = prev.map((x) =>
        x.localId === localId
          ? {
              ...x,
              phase: "pending" as const,
              progressPct: 0,
              errorMessage: null,
            }
          : x
      );
      itemsRef.current = next;
      return next;
    });
  }, []);

  const hasPendingUpload = items.some(
    (x) => x.phase === "pending" || (x.phase === "error" && x.archivoId == null)
  );

  const uploadAll = useCallback(
    async (rutaItemId: number, concurrency = 1): Promise<void> => {
      const current = itemsRef.current;
      const snapshot = current.filter((x) => x.phase === "pending" || x.phase === "error");
      if (snapshot.length === 0) return;
      const generation = ++uploadGenerationRef.current;
      const isStale = () => uploadGenerationRef.current !== generation;
      setSession({ active: true, globalPct: 0, items: [...current] });
      try {
        await uploadQueuedFilesWithConcurrency(rutaItemId, current, {
          concurrency,
          isStale,
          onItemPhase: (localId, phase, progressPct, meta) => {
            if (isStale()) return;
            patchItem(localId, {
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
            setSession((prev) => ({ ...prev, globalPct: pct }));
          },
        });
      } catch {
        /* reconciliación en finally */
      } finally {
        if (!isStale()) {
          const { items: reconciled } = await reconcileMediaQueueAfterUploadAttempt(
            rutaItemId,
            itemsRef.current,
            undefined,
            { isCancelled: isStale }
          );
          if (!isStale()) {
            itemsRef.current = reconciled;
            setItems(reconciled);
            setSession({ active: false, globalPct: 0, items: [...reconciled] });
            notifyMediaUploadSessionSettled();
          }
        }
      }
    },
    [patchItem]
  );

  const clearUploadedFromQueue = useCallback(() => {
    const next = itemsRef.current.filter((x) => {
      if (x.phase === "ready" && x.previewUrl) URL.revokeObjectURL(x.previewUrl);
      return x.phase !== "ready";
    });
    itemsRef.current = next;
    setItems(next);
  }, []);

  const resetAll = useCallback(() => {
    uploadGenerationRef.current += 1;
    setItems((prev) => {
      prev.forEach((x) => {
        if (x.previewUrl) URL.revokeObjectURL(x.previewUrl);
      });
      return [];
    });
    itemsRef.current = [];
    setSession(INITIAL_SESSION);
  }, []);

  const syncQueueItems = useCallback((next: MediaQueuedFile[]) => {
    itemsRef.current = next;
    setItems(next);
    setSession((prev) =>
      prev.active ? { ...prev, items: [...next] } : { ...prev, items: [...next] }
    );
  }, []);

  const getLatestQueueItems = useCallback(() => itemsRef.current, []);

  return {
    items,
    allItems: items,
    getLatestQueueItems,
    getItems,
    addFiles,
    removeItem,
    retryItem,
    hasPendingUpload,
    uploadAll,
    clearUploadedFromQueue,
    resetAll,
    syncQueueItems,
    session,
    patchItem,
  };
}

/**
 * Colas de Completar trabajo aisladas por `rutaItemId` (MEDIA.2C).
 */
export function useCompletarTrabajoMediaQueues(rutaItemId: number | null | undefined) {
  const prevRutaItemIdRef = useRef<number | null>(null);

  useEffect(() => {
    const prev = prevRutaItemIdRef.current;
    const next = rutaItemId ?? null;
    if (prev != null && prev !== next) {
      cancelUploadForRutaItem(prev);
    }
    prevRutaItemIdRef.current = next;
  }, [rutaItemId]);

  const activeId = rutaItemId ?? null;

  const getSnapshot = useCallback(
    () => getRutaItemMediaUploadSnapshot(activeId),
    [activeId]
  );

  const snapshot = useSyncExternalStore(
    subscribeRutaItemMediaUploadStore,
    getSnapshot,
    getSnapshot
  );

  const fotoActaItems = useMemo(
    () => snapshot.items.filter((x) => x.categoria === MEDIA_CATEGORIA_FOTO_ACTA),
    [snapshot.items]
  );
  const fotoDocItems = useMemo(
    () => snapshot.items.filter((x) => x.categoria === MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL),
    [snapshot.items]
  );
  const fotoInspeccionItems = useMemo(
    () => snapshot.items.filter((x) => x.categoria === MEDIA_CATEGORIA_FOTO_INSPECCION),
    [snapshot.items]
  );

  const addFiles = useCallback(
    (categoria: MediaCategoria, files: FileList | File[], serverCount = 0) => {
      if (activeId == null) {
        return { accepted: [], added: 0, skipped: 0, quotaFull: false } satisfies MediaQuotaAddResult;
      }
      return addFilesForRutaItem(activeId, categoria, files, serverCount);
    },
    [activeId]
  );

  const removeItem = useCallback(
    (localId: string) => {
      if (activeId == null) return;
      removeItemForRutaItem(activeId, localId);
    },
    [activeId]
  );

  const uploadAll = useCallback(
    async (expectedRutaItemId: number, concurrency = 1) => {
      if (activeId == null || activeId !== expectedRutaItemId) return;
      await uploadAllForRutaItem(activeId, concurrency);
    },
    [activeId]
  );

  const retryAllPending = useCallback(async () => {
    if (activeId == null) return;
    retryAllRetryableForRutaItem(activeId);
    await uploadAllForRutaItem(activeId, 1);
  }, [activeId]);

  const clearForActiveRutaItem = useCallback(() => {
    if (activeId == null) return;
    clearRutaItemMediaUploadState(activeId);
  }, [activeId]);

  const pauseActiveUpload = useCallback(() => {
    if (activeId == null) return;
    cancelUploadForRutaItem(activeId);
  }, [activeId]);

  const syncQueueItems = useCallback(
    (items: MediaQueuedFile[]) => {
      if (activeId == null) return;
      replaceQueueItemsForRutaItem(activeId, items);
    },
    [activeId]
  );

  const clearUploadedFromQueue = useCallback(() => {
    if (activeId == null) return;
    clearReadyFromQueueForRutaItem(activeId);
  }, [activeId]);

  const addFotoActaFiles = useCallback(
    (files: FileList | File[], serverCount = 0) =>
      addFiles(MEDIA_CATEGORIA_FOTO_ACTA, files, serverCount),
    [addFiles]
  );
  const addFotoDocFiles = useCallback(
    (files: FileList | File[], serverCount = 0) =>
      addFiles(MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL, files, serverCount),
    [addFiles]
  );
  const addFotoInspeccionFiles = useCallback(
    (files: FileList | File[], serverCount = 0) =>
      addFiles(MEDIA_CATEGORIA_FOTO_INSPECCION, files, serverCount),
    [addFiles]
  );

  return useMemo(
    () => ({
      rutaItemId: activeId,
      fotoActa: {
        items: fotoActaItems,
        addFiles: addFotoActaFiles,
        removeItem,
      },
      fotoDoc: {
        items: fotoDocItems,
        addFiles: addFotoDocFiles,
        removeItem,
      },
      fotoInspeccion: {
        items: fotoInspeccionItems,
        addFiles: addFotoInspeccionFiles,
        removeItem,
      },
      hasPendingUpload: snapshot.hasPendingUpload,
      hasRetryableUpload: snapshot.hasRetryableUpload,
      retryableCount: snapshot.retryableCount,
      uploadableCount: snapshot.uploadableCount,
      uploadAll,
      retryAllPending,
      clearForActiveRutaItem,
      pauseActiveUpload,
      syncQueueItems,
      clearUploadedFromQueue,
      session: snapshot.session,
      allItems: snapshot.items,
    }),
    [
      activeId,
      addFotoActaFiles,
      addFotoDocFiles,
      addFotoInspeccionFiles,
      clearForActiveRutaItem,
      pauseActiveUpload,
      clearUploadedFromQueue,
      syncQueueItems,
      fotoActaItems,
      fotoDocItems,
      fotoInspeccionItems,
      removeItem,
      retryAllPending,
      snapshot.hasPendingUpload,
      snapshot.hasRetryableUpload,
      snapshot.retryableCount,
      snapshot.uploadableCount,
      snapshot.items,
      snapshot.session,
      uploadAll,
    ]
  );
}
