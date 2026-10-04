import { useCallback, useMemo, useState } from "react";
import {
  MEDIA_CATEGORIA_FOTO_ACTA,
  MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
  type MediaCategoria1A,
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

export function useMediaCategoryQueue(categoria: MediaCategoria1A) {
  const [items, setItems] = useState<MediaQueuedFile[]>([]);

  const addFiles = useCallback(
    (files: FileList | File[], tipoDocumento: string | null, serverCount = 0) => {
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
              tipoDocumento,
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
            tipoDocumento,
            phase: "pending",
            progressPct: 0,
            errorMessage: null,
            archivoId: null,
            previewUrl: previewForFile(file),
          });
          slotCount += 1;
        }
        return next;
      });
    },
    [categoria]
  );

  const removeItem = useCallback((localId: string) => {
    setItems((prev) => {
      const target = prev.find((x) => x.localId === localId);
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((x) => x.localId !== localId);
    });
  }, []);

  const retryItem = useCallback((localId: string) => {
    setItems((prev) =>
      prev.map((x) =>
        x.localId === localId
          ? { ...x, phase: "pending", progressPct: 0, errorMessage: null }
          : x
      )
    );
  }, []);

  const patchItem = useCallback(
    (localId: string, patch: Partial<MediaQueuedFile>) => {
      setItems((prev) =>
        prev.map((x) => (x.localId === localId ? { ...x, ...patch } : x))
      );
    },
    []
  );

  const hasPendingUpload = useMemo(
    () => items.some((x) => x.phase === "pending" || x.phase === "error"),
    [items]
  );

  const uploadAll = useCallback(
    async (rutaItemId: number, onGlobalProgress?: (pct: number) => void) => {
      const snapshot = [...items];
      await uploadQueuedFilesWithConcurrency(rutaItemId, snapshot, {
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
        onGlobalProgress,
      });
    },
    [items, patchItem]
  );

  const reset = useCallback(() => {
    setItems((prev) => {
      prev.forEach((x) => {
        if (x.previewUrl) URL.revokeObjectURL(x.previewUrl);
      });
      return [];
    });
  }, []);

  return {
    items,
    addFiles,
    removeItem,
    retryItem,
    hasPendingUpload,
    uploadAll,
    reset,
    countInCategory: items.length,
  };
}

export function useCompletarTrabajoMediaQueues() {
  const fotoActa = useMediaCategoryQueue(MEDIA_CATEGORIA_FOTO_ACTA);
  const fotoDoc = useMediaCategoryQueue(MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL);

  const hasPendingUpload = fotoActa.hasPendingUpload || fotoDoc.hasPendingUpload;

  const uploadAll = useCallback(
    async (rutaItemId: number, onGlobalProgress?: (pct: number) => void) => {
      if (fotoActa.hasPendingUpload) {
        await fotoActa.uploadAll(rutaItemId, onGlobalProgress);
      }
      if (fotoDoc.hasPendingUpload) {
        await fotoDoc.uploadAll(rutaItemId, onGlobalProgress);
      }
    },
    [fotoActa, fotoDoc]
  );

  return {
    fotoActa,
    fotoDoc,
    hasPendingUpload,
    uploadAll,
    resetAll: () => {
      fotoActa.reset();
      fotoDoc.reset();
    },
  };
}
