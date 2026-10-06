import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import {
  MEDIA_CATEGORIA_FOTO_ACTA,
  MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
  MEDIA_CATEGORIA_FOTO_INSPECCION,
  type MediaCategoria,
} from "../mediaConstants";
import { validateLocalMediaFile } from "../mediaFileValidation";
import type { MediaQueuedFile } from "../mediaTypes";
import { uploadQueuedFilesWithConcurrency } from "../mediaUploadPipeline";
import { sliceFilesToAvailableQuota, type MediaQuotaAddResult } from "../../../Containers/CompletarTrabajos/utils/completarTrabajoMediaQuota";
import {
  addFilesForRutaItem,
  cancelUploadForRutaItem,
  clearRutaItemMediaUploadState,
  getRutaItemMediaUploadSnapshot,
  removeItemForRutaItem,
  retryAllRetryableForRutaItem,
  subscribeRutaItemMediaUploadStore,
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
export function useMediaUploadCoordinator() {
  const [items, setItems] = useState<MediaQueuedFile[]>([]);
  const itemsRef = useRef<MediaQueuedFile[]>([]);
  const [session, setSession] = useState<MediaUploadSessionState>(INITIAL_SESSION);

  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  const getItems = useCallback(
    (categoria: MediaCategoria) => items.filter((x) => x.categoria === categoria),
    [items]
  );

  const patchItem = useCallback((localId: string, patch: Partial<MediaQueuedFile>) => {
    setItems((prev) => prev.map((x) => (x.localId === localId ? { ...x, ...patch } : x)));
    setSession((prev) =>
      prev.active
        ? {
            ...prev,
            items: prev.items.map((x) => (x.localId === localId ? { ...x, ...patch } : x)),
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
    []
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
      setSession({ active: true, globalPct: 0, items: [...current] });
      try {
        await uploadQueuedFilesWithConcurrency(rutaItemId, current, {
          concurrency,
          onItemPhase: (localId, phase, progressPct, meta) => {
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
            setSession((prev) => ({ ...prev, globalPct: pct }));
          },
        });
      } finally {
        setSession((prev) => ({ ...prev, active: false }));
      }
    },
    [patchItem]
  );

  const clearUploadedFromQueue = useCallback(() => {
    setItems((prev) => {
      prev.forEach((x) => {
        if (x.phase === "ready" && x.previewUrl) URL.revokeObjectURL(x.previewUrl);
      });
      return prev.filter((x) => x.phase !== "ready");
    });
  }, []);

  const resetAll = useCallback(() => {
    setItems((prev) => {
      prev.forEach((x) => {
        if (x.previewUrl) URL.revokeObjectURL(x.previewUrl);
      });
      return [];
    });
    setSession(INITIAL_SESSION);
  }, []);

  return {
    items,
    allItems: items,
    getItems,
    addFiles,
    removeItem,
    retryItem,
    hasPendingUpload,
    uploadAll,
    clearUploadedFromQueue,
    resetAll,
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

  const snapshot = useSyncExternalStore(
    subscribeRutaItemMediaUploadStore,
    () => getRutaItemMediaUploadSnapshot(rutaItemId),
    () => getRutaItemMediaUploadSnapshot(rutaItemId)
  );

  const activeId = rutaItemId ?? null;

  const getItems = useCallback(
    (categoria: MediaCategoria) =>
      snapshot.items.filter((x) => x.categoria === categoria),
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

  return {
    rutaItemId: activeId,
    fotoActa: {
      items: getItems(MEDIA_CATEGORIA_FOTO_ACTA),
      addFiles: (files: FileList | File[], serverCount = 0) =>
        addFiles(MEDIA_CATEGORIA_FOTO_ACTA, files, serverCount),
      removeItem,
    },
    fotoDoc: {
      items: getItems(MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL),
      addFiles: (files: FileList | File[], serverCount = 0) =>
        addFiles(MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL, files, serverCount),
      removeItem,
    },
    fotoInspeccion: {
      items: getItems(MEDIA_CATEGORIA_FOTO_INSPECCION),
      addFiles: (files: FileList | File[], serverCount = 0) =>
        addFiles(MEDIA_CATEGORIA_FOTO_INSPECCION, files, serverCount),
      removeItem,
    },
    hasPendingUpload: snapshot.hasPendingUpload,
    hasRetryableUpload: snapshot.hasRetryableUpload,
    retryableCount: snapshot.retryableCount,
    uploadAll,
    retryAllPending,
    clearForActiveRutaItem,
    session: snapshot.session,
    allItems: snapshot.items,
  };
}
