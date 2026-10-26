import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { Stack, Typography } from "@mui/material";
import { deleteArchivo, getRutaItemArchivos } from "../../../api/mediaApi";
import { useAppFeedback } from "../../../components/feedback";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import {
  MEDIA_CATEGORY_LABELS,
  MEDIA_CATEGORIA_FOTO_ACTA,
  MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
  MEDIA_CATEGORIA_FOTO_INSPECCION,
  MEDIA_RUTA_ITEM_GALLERIES,
} from "../mediaConstants";
import type { MediaArchivoListItem, RutaItemArchivosListResponse } from "../mediaTypes";
import type { MediaCategoria } from "../mediaConstants";
import { useMediaUploadCoordinator } from "../hooks/useMediaUploadCoordinator";
import {
  MEDIA_UPLOAD_ORIGIN_COMPLETAR_TRABAJO,
  MEDIA_UPLOAD_ORIGIN_MIS_TRABAJOS,
} from "../mediaUploadOrigin";
import {
  countUploadableQueueItems,
  MANUAL_MEDIA_GALLERY_REFRESH_HINT,
  MANUAL_MEDIA_PARTIAL_MESSAGE,
  MANUAL_MEDIA_RELOAD_HINT,
  runManualMediaSave,
  type ManualMediaSaveOutcome,
} from "../utils/actuacionManualMediaSave";
import type { MediaUploadOrigin } from "../mediaUploadOrigin";
import { MediaGalleryCategoryBlock } from "./MediaGalleryCategoryBlock";
import { MediaPreviewDialog } from "./MediaPreviewDialog";
import { useCrudDialogScrollContainer } from "../../../components/crudDialog";
import { useMediaUploadPanelHold } from "../hooks/useMediaUploadPanelHold";
import { useScrollMediaUploadPanelOnUploadStart } from "../hooks/useScrollMediaUploadPanelOnUploadStart";
import { scheduleScrollMediaUploadPanelIntoView } from "../utils/scrollMediaUploadPanelIntoView";
import { MediaUploadProgress } from "./MediaUploadProgress";
type Props = {
  rutaItemId: number | null | undefined;
  readOnly?: boolean;
  hideTitle?: boolean;
  /** Mis trabajos: encolar localmente y subir solo con GUARDAR FOTOS. */
  manualSave?: boolean;
  uploadOrigin?: MediaUploadOrigin;
  onQueueStatsChange?: (stats: { uploadable: number; hasRetryable: boolean }) => void;
};

export type ActuacionMediaGalleryHandle = {
  saveQueuedPhotos: () => Promise<ManualMediaSaveOutcome>;
  pendingSaveCount: () => number;
  isUploadInProgress: () => boolean;
  discardLocalQueue: () => void;
  scrollUploadPanelIntoView: () => void;
};

function serverItemsForCategoria(
  data: RutaItemArchivosListResponse | null,
  categoria: MediaCategoria
): MediaArchivoListItem[] {
  if (!data) return [];
  switch (categoria) {
    case MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL:
      return data.foto_documentacion_local;
    case MEDIA_CATEGORIA_FOTO_ACTA:
      return data.foto_acta;
    case MEDIA_CATEGORIA_FOTO_INSPECCION:
      return data.foto_inspeccion;
    default:
      return [];
  }
}

export const ActuacionMediaGallery = forwardRef<ActuacionMediaGalleryHandle, Props>(
  function ActuacionMediaGallery(
    {
      rutaItemId,
      readOnly = false,
      hideTitle = false,
      manualSave = false,
      uploadOrigin = manualSave ? MEDIA_UPLOAD_ORIGIN_MIS_TRABAJOS : undefined,
      onQueueStatsChange,
    },
    ref
  ) {
    const feedback = useAppFeedback();
    const coordinator = useMediaUploadCoordinator(
      uploadOrigin ??
        (manualSave ? MEDIA_UPLOAD_ORIGIN_MIS_TRABAJOS : MEDIA_UPLOAD_ORIGIN_COMPLETAR_TRABAJO)
    );
    const { resetAll: resetUploadQueue } = coordinator;
    const [data, setData] = useState<RutaItemArchivosListResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [preview, setPreview] = useState<{
      categoria: MediaCategoria;
      archivoId: number;
    } | null>(null);
    const [deletingId, setDeletingId] = useState<number | null>(null);
    const [uploading, setUploading] = useState(false);
    const uploadInFlightRef = useRef(false);
    const uploadProgressPanelRef = useRef<HTMLElement | null>(null);
    const dialogScrollContainerRef = useCrudDialogScrollContainer();

    const refreshGalleryFromServer = useCallback(
      async (options?: { silent?: boolean }) => {
        if (!rutaItemId) return;
        try {
          if (!options?.silent) {
            setError(null);
          }
          const res = await getRutaItemArchivos(rutaItemId);
          setData(res);
        } catch {
          if (!options?.silent) {
            setError("No se pudieron cargar los archivos.");
          }
        }
      },
      [rutaItemId]
    );

    useEffect(() => {
      void refreshGalleryFromServer();
    }, [refreshGalleryFromServer]);

    useEffect(() => {
      resetUploadQueue();
      setError(null);
    }, [rutaItemId, resetUploadQueue]);

    useEffect(() => {
      if (!onQueueStatsChange) return;
      const uploadable = countUploadableQueueItems(coordinator.allItems);
      const hasRetryable = coordinator.allItems.some(
        (x) => x.phase === "error" || x.phase === "pending"
      );
      onQueueStatsChange({ uploadable, hasRetryable: hasRetryable && uploadable > 0 });
    }, [coordinator.allItems, onQueueStatsChange]);

    const saveQueuedPhotos = useCallback(async (): Promise<ManualMediaSaveOutcome> => {
      if (!rutaItemId || uploadInFlightRef.current) return "empty";
      if (countUploadableQueueItems(coordinator.allItems) === 0) return "empty";

      uploadInFlightRef.current = true;
      setUploading(true);
      setError(null);
      scheduleScrollMediaUploadPanelIntoView(
        uploadProgressPanelRef.current,
        dialogScrollContainerRef?.current ?? null
      );
      try {
        const { outcome, refreshFailed } = await runManualMediaSave({
          rutaItemId,
          uploadAll: coordinator.uploadAll,
          getQueueItems: coordinator.getLatestQueueItems,
          applyQueueItems: coordinator.syncQueueItems,
          clearUploadedFromQueue: coordinator.clearUploadedFromQueue,
          reloadServer: () => refreshGalleryFromServer({ silent: true }),
        });

        if (outcome === "success") {
          if (refreshFailed) {
            feedback.info(MANUAL_MEDIA_GALLERY_REFRESH_HINT);
          } else if (!manualSave) {
            feedback.success("Archivos subidos correctamente.");
          }
        } else if (outcome === "partial") {
          setError(null);
          feedback.info(MANUAL_MEDIA_PARTIAL_MESSAGE);
        }
        return outcome;
      } finally {
        uploadInFlightRef.current = false;
        setUploading(false);
      }
    }, [coordinator, feedback, manualSave, refreshGalleryFromServer, rutaItemId]);

    const runAutoUploadAfterAdd = useCallback(async () => {
      if (manualSave || !rutaItemId) return;
      await saveQueuedPhotos();
    }, [manualSave, rutaItemId, saveQueuedPhotos]);

    useImperativeHandle(
      ref,
      () => ({
        saveQueuedPhotos,
        pendingSaveCount: () => countUploadableQueueItems(coordinator.allItems),
        isUploadInProgress: () => uploading || coordinator.session.active || uploadInFlightRef.current,
        discardLocalQueue: () => resetUploadQueue(),
        scrollUploadPanelIntoView: () => {
          scheduleScrollMediaUploadPanelIntoView(
            uploadProgressPanelRef.current,
            dialogScrollContainerRef?.current ?? null
          );
        },
      }),
      [
        coordinator.allItems,
        coordinator.session.active,
        dialogScrollContainerRef,
        resetUploadQueue,
        saveQueuedPhotos,
        uploading,
      ]
    );

    const handleAddFiles = useCallback(
      (categoria: MediaCategoria, files: FileList | File[]) => {
        const serverCount = serverItemsForCategoria(data, categoria).length;
        coordinator.addFiles(categoria, files, serverCount);
        if (!manualSave) {
          queueMicrotask(() => {
            void runAutoUploadAfterAdd();
          });
        }
      },
      [coordinator, data, manualSave, runAutoUploadAfterAdd]
    );

    const previewItems = useMemo(
      () => (preview ? serverItemsForCategoria(data, preview.categoria) : []),
      [data, preview]
    );
    const previewCategoryLabel = preview ? MEDIA_CATEGORY_LABELS[preview.categoria] : "";

    useEffect(() => {
      if (!preview) return;
      if (!previewItems.some((i) => i.archivo_id === preview.archivoId)) {
        setPreview(null);
      }
    }, [preview, previewItems]);

    const openPreviewHandlers = useMemo(() => {
      const handlers = new Map<MediaCategoria, (archivoId: number) => void>();
      for (const gallery of MEDIA_RUTA_ITEM_GALLERIES) {
        const categoria = gallery.categoria;
        handlers.set(categoria, (archivoId: number) => {
          setPreview({ categoria, archivoId });
        });
      }
      return handlers;
    }, []);

    const handleDelete = useCallback(
      async (archivoId: number) => {
        if (!window.confirm("¿Eliminar este archivo? Esta acción no se puede deshacer.")) return;
        setDeletingId(archivoId);
        try {
          await deleteArchivo(archivoId);
          await refreshGalleryFromServer();
          feedback.success("Archivo eliminado.");
        } catch {
          feedback.error("No se pudo eliminar el archivo.");
        } finally {
          setDeletingId(null);
        }
      },
      [feedback, refreshGalleryFromServer]
    );

    const onDeleteById = useCallback(
      (archivoId: number) => {
        void handleDelete(archivoId);
      },
      [handleDelete]
    );

    const handleRetryUpload = useCallback(
      async (localId: string) => {
        coordinator.retryItem(localId);
        if (manualSave) return;
        await runAutoUploadAfterAdd();
      },
      [coordinator, manualSave, runAutoUploadAfterAdd]
    );

    const addFilesByCategoria = useMemo(() => {
      const map = new Map<MediaCategoria, (files: FileList | File[]) => void>();
      for (const gallery of MEDIA_RUTA_ITEM_GALLERIES) {
        map.set(gallery.categoria, (files) => handleAddFiles(gallery.categoria, files));
      }
      return map;
    }, [handleAddFiles]);

    const progressItems =
      coordinator.session.items.length > 0 ? coordinator.session.items : coordinator.allItems;
    const sessionActive = coordinator.session.active || uploading;
    const { visible: progressPanelVisible } = useMediaUploadPanelHold(sessionActive, progressItems);
    useScrollMediaUploadPanelOnUploadStart(
      sessionActive,
      progressPanelVisible,
      uploadProgressPanelRef,
      dialogScrollContainerRef
    );

    if (!rutaItemId) {
      return (
        <Typography variant="body2" sx={{ color: GLASS_COLORS.textMuted }}>
          No hay ítem de ruta asociado para archivos.
        </Typography>
      );
    }

    const pendingQueueTitle = manualSave ? "Fotos pendientes de guardar" : "Fotos pendientes de carga";
    const pendingPhaseLabel = manualSave ? "Pendiente de guardar" : "Pendiente de carga";

    return (
      <>
        <MediaUploadProgress
          ref={uploadProgressPanelRef}
          open={progressPanelVisible}
          sessionActive={sessionActive}
          globalPct={coordinator.session.globalPct}
          items={progressItems}
          onRetry={manualSave ? undefined : (id) => void handleRetryUpload(id)}
        />
        <MediaPreviewDialog
          open={preview != null}
          items={previewItems}
          activeArchivoId={preview?.archivoId ?? null}
          categoryLabel={previewCategoryLabel}
          onClose={() => setPreview(null)}
        />
        <Stack spacing={2}>
        {!hideTitle ? (
          <Typography variant="subtitle1" sx={{ color: GLASS_COLORS.textPrimary }}>
            Archivos de la actuación
          </Typography>
        ) : null}
        {manualSave ? (
          <Typography variant="body2" sx={{ color: GLASS_COLORS.textMuted }}>
            Las fotos seleccionadas quedan pendientes hasta que presiones GUARDAR FOTOS o CONTINUAR
            SUBIDA. {MANUAL_MEDIA_RELOAD_HINT}
          </Typography>
        ) : null}
          {error ? <Typography color="error">{error}</Typography> : null}
          {MEDIA_RUTA_ITEM_GALLERIES.map((gallery) => (
            <MediaGalleryCategoryBlock
              key={gallery.categoria}
              gallery={gallery}
              serverItems={serverItemsForCategoria(data, gallery.categoria)}
              queueItems={coordinator.getItems(gallery.categoria)}
              readOnly={readOnly}
              deletingId={deletingId}
              uploading={uploading}
              sessionActive={coordinator.session.active}
              manualSave={manualSave}
              pendingQueueTitle={pendingQueueTitle}
              pendingPhaseLabel={pendingPhaseLabel}
              onOpenById={openPreviewHandlers.get(gallery.categoria)!}
              onDeleteById={readOnly ? undefined : onDeleteById}
              onAddFiles={addFilesByCategoria.get(gallery.categoria)!}
              onRemove={coordinator.removeItem}
              onRetry={manualSave ? undefined : handleRetryUpload}
            />
          ))}
        </Stack>
      </>
    );
  }
);
