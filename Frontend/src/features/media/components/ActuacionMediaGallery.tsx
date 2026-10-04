import { useCallback, useEffect, useState } from "react";
import { Box, ImageList, Stack, Typography } from "@mui/material";
import { deleteArchivo, getRutaItemArchivos } from "../../../api/mediaApi";
import { useAppFeedback } from "../../../components/feedback";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import {
  MEDIA_CATEGORY_CONFIG_1A,
  MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
} from "../mediaConstants";
import type { MediaArchivoListItem } from "../mediaTypes";
import type { MediaCategoria1A } from "../mediaConstants";
import { MEDIA_CATEGORIA_FOTO_ACTA } from "../mediaConstants";
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

function CategoryGalleryBlock({
  categoria,
  serverItems,
  queueItems,
  readOnly,
  uploading,
  onAddFiles,
  onRemoveQueue,
  onRetryQueue,
  onOpen,
}: {
  categoria: MediaCategoria1A;
  serverItems: MediaArchivoListItem[];
  queueItems: import("../mediaTypes").MediaQueuedFile[];
  readOnly?: boolean;
  uploading: boolean;
  onAddFiles: (files: FileList) => void;
  onRemoveQueue: (localId: string) => void;
  onRetryQueue: (localId: string) => void;
  onOpen: (item: MediaArchivoListItem) => void;
}) {
  const config = MEDIA_CATEGORY_CONFIG_1A[categoria];

  if (!readOnly) {
    return (
      <Box sx={{ mt: serverItems.length > 0 ? 2 : 0 }}>
        <MediaUploadSection
          categoria={categoria}
          items={queueItems}
          serverCount={serverItems.length}
          onAddFiles={onAddFiles}
          onRemove={onRemoveQueue}
          onRetry={onRetryQueue}
          disabled={uploading}
        />
      </Box>
    );
  }

  return (
    <Box sx={{ mb: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 0.5 }}>
        <Box>
          <Typography variant="subtitle2" sx={{ color: GLASS_COLORS.textPrimary }}>
            {config.titulo}
          </Typography>
          <Typography variant="body2" sx={{ color: GLASS_COLORS.textMuted, fontStyle: "italic", mt: 0.25 }}>
            {config.ejemplos}
          </Typography>
        </Box>
        <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted }}>
          {serverItems.length} / {config.cupo}
        </Typography>
      </Stack>
      {serverItems.length === 0 ? (
        <Typography variant="body2" sx={{ color: GLASS_COLORS.textMuted, py: 1 }}>
          Sin archivos cargados.
        </Typography>
      ) : (
        <ImageList cols={3} gap={8} sx={{ m: 0 }}>
          {serverItems.map((item) => (
            <MediaThumbnailTile key={item.archivo_id} item={item} onOpen={() => onOpen(item)} />
          ))}
        </ImageList>
      )}
    </Box>
  );
}

export function ActuacionMediaGallery({ rutaItemId, readOnly = false, hideTitle = false }: Props) {
  const feedback = useAppFeedback();
  const coordinator = useMediaUploadCoordinator();
  const [data, setData] = useState<{
    foto_acta: MediaArchivoListItem[];
    foto_documentacion_local: MediaArchivoListItem[];
  } | null>(null);
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
    if (!rutaItemId || !coordinator.hasPendingUpload) return;
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
    (categoria: MediaCategoria1A, files: FileList) => {
      const serverCount =
        categoria === MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL
          ? (data?.foto_documentacion_local.length ?? 0)
          : (data?.foto_acta.length ?? 0);
      coordinator.addFiles(categoria, files, serverCount);
      void runUpload();
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

  const renderCategory = (categoria: MediaCategoria1A, serverItems: MediaArchivoListItem[]) => {
    const config = MEDIA_CATEGORY_CONFIG_1A[categoria];
    const queueItems = coordinator.getItems(categoria);

    return (
      <Box key={categoria} sx={{ mb: 3 }}>
        {!readOnly ? (
          <>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 0.5 }}>
              <Box>
                <Typography variant="subtitle2" sx={{ color: GLASS_COLORS.textPrimary }}>
                  {config.titulo}
                </Typography>
                <Typography
                  variant="body2"
                  sx={{ color: GLASS_COLORS.textMuted, fontStyle: "italic", mt: 0.25 }}
                >
                  {config.ejemplos}
                </Typography>
              </Box>
              <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted }}>
                {serverItems.length} / {config.cupo}
              </Typography>
            </Stack>
            {serverItems.length === 0 ? (
              <Typography variant="body2" sx={{ color: GLASS_COLORS.textMuted, py: 1 }}>
                Sin archivos cargados.
              </Typography>
            ) : (
              <ImageList cols={3} gap={8} sx={{ m: 0 }}>
                {serverItems.map((item) => (
                  <MediaThumbnailTile
                    key={item.archivo_id}
                    item={item}
                    onOpen={() => setPreview(item)}
                    onDelete={() => void handleDelete(item.archivo_id)}
                    deleting={deletingId === item.archivo_id}
                  />
                ))}
              </ImageList>
            )}
            <CategoryGalleryBlock
              categoria={categoria}
              serverItems={serverItems}
              queueItems={queueItems}
              readOnly={false}
              uploading={uploading}
              onAddFiles={(files) => handleAddFiles(categoria, files)}
              onRemoveQueue={coordinator.removeItem}
              onRetryQueue={(id) => void handleRetryUpload(id)}
              onOpen={setPreview}
            />
          </>
        ) : (
          <CategoryGalleryBlock
            categoria={categoria}
            serverItems={serverItems}
            queueItems={[]}
            readOnly
            uploading={false}
            onAddFiles={() => undefined}
            onRemoveQueue={() => undefined}
            onRetryQueue={() => undefined}
            onOpen={setPreview}
          />
        )}
      </Box>
    );
  };

  return (
    <>
      <MediaUploadProgress
        open={coordinator.session.active || uploading}
        globalPct={coordinator.session.globalPct}
        items={coordinator.session.items.length > 0 ? coordinator.session.items : coordinator.allItems}
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
        {renderCategory(MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL, data?.foto_documentacion_local ?? [])}
        {renderCategory(MEDIA_CATEGORIA_FOTO_ACTA, data?.foto_acta ?? [])}
      </Stack>
    </>
  );
}
