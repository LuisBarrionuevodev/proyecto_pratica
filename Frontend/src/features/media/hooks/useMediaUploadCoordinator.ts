import { useCallback, useEffect, useRef, useState } from "react";
import {
  MEDIA_CATEGORIA_FOTO_ACTA,
  MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
  MEDIA_CATEGORIA_FOTO_INSPECCION,
  type MediaCategoria,
} from "../mediaConstants";
import { validateLocalMediaFile } from "../mediaFileValidation";
import type { MediaQueuedFile } from "../mediaTypes";
import { uploadQueuedFilesWithConcurrency } from "../mediaUploadPipeline";

function newLocalId(): string {
  return `mq-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function previewForFile(file: File): string | null {
  if (file.type.startsWith("image/")) {
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
    (categoria: MediaCategoria, files: FileList | File[], serverCount = 0) => {
      const list = Array.from(files);
      setItems((prev) => {
        const next = [...prev];
        let slotCount =
          serverCount +
          next.filter((x) => x.categoria === categoria && x.phase !== "error").length;
        for (const file of list) {
          const err = validateLocalMediaFile(file, categoria, slotCount);
          if (err) {
            next.push({
              localId: newLocalId(),
              file,
              categoria,
              tipoDocumento: null,
              phase: "error",
              progressPct: 0,
              errorMessage: err,
              archivoId: null,
              previewUrl: previewForFile(file),
            });
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
        }
        itemsRef.current = next;
        return next;
      });
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
          ? { ...x, phase: "pending" as const, progressPct: 0, errorMessage: null }
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
    async (rutaItemId: number): Promise<void> => {
      const current = itemsRef.current;
      const snapshot = current.filter(
        (x) => x.phase === "pending" || (x.phase === "error" && !x.archivoId)
      );
      if (snapshot.length === 0) return;
      setSession({ active: true, globalPct: 0, items: [...current] });
      try {
        await uploadQueuedFilesWithConcurrency(rutaItemId, current, {
          onItemPhase: (localId, phase, progressPct, meta) => {
            patchItem(localId, {
              phase,
              progressPct: progressPct ?? 0,
              ...(meta?.archivoId != null ? { archivoId: meta.archivoId } : {}),
              ...(phase === "error"
                ? { errorMessage: meta?.errorMessage ?? "Error al subir el archivo." }
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

/** Colas de Completar trabajo (documentación, actas e inspección). */
export function useCompletarTrabajoMediaQueues() {
  const coord = useMediaUploadCoordinator();

  return {
    fotoActa: {
      items: coord.getItems(MEDIA_CATEGORIA_FOTO_ACTA),
      addFiles: (files: FileList | File[], serverCount = 0) =>
        coord.addFiles(MEDIA_CATEGORIA_FOTO_ACTA, files, serverCount),
      removeItem: coord.removeItem,
      retryItem: coord.retryItem,
    },
    fotoDoc: {
      items: coord.getItems(MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL),
      addFiles: (files: FileList | File[], serverCount = 0) =>
        coord.addFiles(MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL, files, serverCount),
      removeItem: coord.removeItem,
      retryItem: coord.retryItem,
    },
    fotoInspeccion: {
      items: coord.getItems(MEDIA_CATEGORIA_FOTO_INSPECCION),
      addFiles: (files: FileList | File[], serverCount = 0) =>
        coord.addFiles(MEDIA_CATEGORIA_FOTO_INSPECCION, files, serverCount),
      removeItem: coord.removeItem,
      retryItem: coord.retryItem,
    },
    hasPendingUpload: coord.hasPendingUpload,
    uploadAll: coord.uploadAll,
    resetAll: coord.resetAll,
    session: coord.session,
    allItems: coord.allItems,
    retryItem: coord.retryItem,
  };
}
