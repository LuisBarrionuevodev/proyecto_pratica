import { useCallback, useEffect, useState } from "react";
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
import { MediaPreviewDialog } from "./MediaPreviewDialog";
import { MediaThumbnailTile } from "./MediaThumbnailTile";
import { MediaUploadProgress } from "./MediaUploadProgress";
import { MediaUploadSection } from "./MediaUploadSection";

type Props = {
  rutaItemId: number | null | undefined;
  readOnly?: boolean;
  hideTitle?: boolean;
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

export function ActuacionMediaGallery({ rutaItemId, readOnly = false, hideTitle = false }: Props) {
  const feedback = useAppFeedback();
  const coordinator = useMediaUploadCoordinator();
  const [data, setData] = useState<RutaItemArchivosListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<MediaArchivoListItem | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);

  const load = useCallback(async () => {
    if (!rutaItemId) return;
    try {
      setError(null);
      const res = await getRutaItemArchivos(rutaItemId);
      setData(res);
    } catch {
      setError("No se pudieron cargar los archivos.");
    }
  }, [rutaItemId]);

  useEffect(() => {
    void load();
  }, [load]);

  const runUpload = useCallback(async () => {
    if (!rutaItemId) return;
    setUploading(true);
    try {
      await coordinator.uploadAll(rutaItemId);
      coordinator.clearUploadedFromQueue();
      await load();
      feedback.success("Archivos subidos correctamente.");
    } catch {
      feedback.error("No se pudieron subir todos los archivos. Revise los fallidos e intente de nuevo.");
    } finally {
      setUploading(false);
    }
  }, [rutaItemId, coordinator, load, feedback]);

  const handleAddFiles = useCallback(
    (categoria: MediaCategoria, files: FileList) => {
      const serverCount = serverItemsForCategoria(data, categoria).length;
      coordinator.addFiles(categoria, files, serverCount);
      queueMicrotask(() => {
        void runUpload();
      });
    },
    [coordinator, data, runUpload]
  );

  const handleDelete = async (archivoId: number) => {
    if (!window.confirm("¿Eliminar este archivo? Esta acción no se puede deshacer.")) return;
    setDeletingId(archivoId);
    try {
      await deleteArchivo(archivoId);
      await load();
      feedback.success("Archivo eliminado.");
    } catch {
      feedback.error("No se pudo eliminar el archivo.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleRetryUpload = async (localId: string) => {
    coordinator.retryItem(localId);
    await runUpload();
  };

  if (!rutaItemId) {
    return (
      <Typography variant="body2" sx={{ color: GLASS_COLORS.textMuted }}>
        No hay ítem de ruta asociado para archivos.
      </Typography>
    );
  }

  return (
    <>
      <MediaUploadProgress
        open={coordinator.session.active || uploading}
        globalPct={coordinator.session.globalPct}
        items={
          coordinator.session.items.length > 0 ? coordinator.session.items : coordinator.allItems
        }
        onRetry={(id) => void handleRetryUpload(id)}
      />
      <MediaPreviewDialog open={preview != null} item={preview} onClose={() => setPreview(null)} />
      <Stack spacing={2}>
        {!hideTitle ? (
          <Typography variant="subtitle1" sx={{ color: GLASS_COLORS.textPrimary }}>
            Archivos de la actuación
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
                  onRetry={(id) => void handleRetryUpload(id)}
                  disabled={uploading}
                />
              ) : null}
            </Box>
          );
        })}
      </Stack>
    </>
  );
}
