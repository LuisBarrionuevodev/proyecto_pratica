import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { Box, ImageList, Stack, Typography } from "@mui/material";
import { deleteArchivo, getRutaItemArchivos } from "../../../api/mediaApi";
import { useAppFeedback } from "../../../components/feedback";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import {
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
  MANUAL_MEDIA_PARTIAL_MESSAGE,
  MANUAL_MEDIA_RELOAD_HINT,
  runManualMediaSave,
  type ManualMediaSaveOutcome,
} from "../utils/actuacionManualMediaSave";
import type { MediaUploadOrigin } from "../mediaUploadOrigin";
import { MediaPreviewDialog } from "./MediaPreviewDialog";
import { MediaThumbnailTile } from "./MediaThumbnailTile";
import { MediaUploadProgress } from "./MediaUploadProgress";
import { MediaUploadSection } from "./MediaUploadSection";

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
    const [preview, setPreview] = useState<MediaArchivoListItem | null>(null);
    const [deletingId, setDeletingId] = useState<number | null>(null);
    const [uploading, setUploading] = useState(false);
    const uploadInFlightRef = useRef(false);

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
      try {
        const { outcome, refreshFailed } = await runManualMediaSave({
          rutaItemId,
          uploadAll: coordinator.uploadAll,
          getQueueItems: coordinator.getLatestQueueItems,
          clearUploadedFromQueue: coordinator.clearUploadedFromQueue,
          reloadServer: () => refreshGalleryFromServer({ silent: true }),
        });

        if (outcome === "success") {
          if (refreshFailed) {
            feedback.info("Las fotos se guardaron; no se pudo refrescar la vista. Reabrí el trabajo si no las ves.");
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
      }),
      [coordinator.allItems, coordinator.session.active, resetUploadQueue, saveQueuedPhotos, uploading]
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

    const handleDelete = async (archivoId: number) => {
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
    };

    const handleRetryUpload = async (localId: string) => {
      coordinator.retryItem(localId);
      if (manualSave) return;
      await runAutoUploadAfterAdd();
    };

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
          open={coordinator.session.active || uploading}
          globalPct={coordinator.session.globalPct}
          items={
            coordinator.session.items.length > 0 ? coordinator.session.items : coordinator.allItems
          }
          onRetry={manualSave ? undefined : (id) => void handleRetryUpload(id)}
        />
        <MediaPreviewDialog open={preview != null} item={preview} onClose={() => setPreview(null)} />
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
          {MEDIA_RUTA_ITEM_GALLERIES.map((gallery) => {
            const serverItems = serverItemsForCategoria(data, gallery.categoria);
            const queueItems = coordinator.getItems(gallery.categoria);
            const localPending = queueItems.filter((x) => x.phase !== "ready").length;
            const used = serverItems.length + localPending;

            return (
              <Box key={gallery.categoria} sx={{ mb: 2 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 0.5 }}>
                  <Box>
                    <Typography variant="subtitle2" sx={{ color: GLASS_COLORS.textPrimary }}>
                      {gallery.titulo}
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{ color: GLASS_COLORS.textMuted, fontStyle: "italic", mt: 0.25 }}
                    >
                      {gallery.ejemplos}
                    </Typography>
                  </Box>
                  <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted }}>
                    {used} / {gallery.cupo}
                  </Typography>
                </Stack>
                {serverItems.length === 0 ? (
                  <Typography variant="body2" sx={{ color: GLASS_COLORS.textMuted, py: 1 }}>
                    Sin archivos cargados.
                  </Typography>
                ) : (
                  <ImageList cols={3} gap={8} sx={{ m: 0, mb: 1 }}>
                    {serverItems.map((item) => (
                      <MediaThumbnailTile
                        key={item.archivo_id}
                        item={item}
                        onOpen={() => setPreview(item)}
                        onDelete={readOnly ? undefined : () => void handleDelete(item.archivo_id)}
                        deleting={deletingId === item.archivo_id}
                      />
                    ))}
                  </ImageList>
                )}
                {!readOnly ? (
                  <MediaUploadSection
                    embedded
                    categoria={gallery.categoria}
                    items={queueItems}
                    serverCount={serverItems.length}
                    onAddFiles={(files) => handleAddFiles(gallery.categoria, files)}
                    onRemove={coordinator.removeItem}
                    onRetry={manualSave ? undefined : (id) => void handleRetryUpload(id)}
                    disabled={uploading || coordinator.session.active}
                    pendingQueueTitle={pendingQueueTitle}
                    pendingPhaseLabel={pendingPhaseLabel}
                  />
                ) : null}
              </Box>
            );
          })}
        </Stack>
      </>
    );
  }
);
