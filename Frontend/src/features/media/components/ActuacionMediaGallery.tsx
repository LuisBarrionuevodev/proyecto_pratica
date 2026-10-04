import { useCallback, useEffect, useState } from "react";
import {
  Box,
  Button,
  ImageList,
  ImageListItem,
  ImageListItemBar,
  Stack,
  Typography,
} from "@mui/material";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import { deleteArchivo, getRutaItemArchivos } from "../../../api/mediaApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import {
  MEDIA_CATEGORY_LABELS,
  MEDIA_CATEGORY_MAX,
  MEDIA_CATEGORIA_FOTO_ACTA,
  MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL,
  type MediaCategoria1A,
} from "../mediaConstants";
import type { MediaArchivoListItem } from "../mediaTypes";
import { MediaPreviewDialog } from "./MediaPreviewDialog";
import { MediaUploadSection } from "./MediaUploadSection";
import { useMediaCategoryQueue } from "../hooks/useMediaCategoryQueue";

type Props = {
  rutaItemId: number | null | undefined;
  readOnly?: boolean;
  /** Oculta el título principal cuando el padre ya usa un overline (p. ej. modal gestión). */
  hideTitle?: boolean;
};

function GalleryTiles({
  items,
  onOpen,
}: {
  items: MediaArchivoListItem[];
  onOpen: (item: MediaArchivoListItem) => void;
}) {
  if (items.length === 0) {
    return (
      <Typography variant="body2" sx={{ color: GLASS_COLORS.textMuted, py: 1 }}>
        Sin archivos cargados.
      </Typography>
    );
  }
  return (
    <ImageList cols={3} gap={8} sx={{ m: 0 }}>
      {items.map((item) => {
        const isImg = item.content_type.startsWith("image/");
        return (
          <ImageListItem
            key={item.archivo_id}
            sx={{ cursor: "pointer" }}
            onClick={() => onOpen(item)}
          >
            <Box
              sx={{
                height: 96,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                bgcolor: "action.hover",
                borderRadius: 1,
              }}
            >
              {isImg ? (
                <Typography variant="caption" sx={{ px: 1, textAlign: "center" }}>
                  Imagen
                </Typography>
              ) : (
                <PictureAsPdfIcon />
              )}
            </Box>
            <ImageListItemBar title={item.original_filename} subtitle={item.tipo_documento ?? undefined} />
          </ImageListItem>
        );
      })}
    </ImageList>
  );
}

function CategoryBlock({
  categoria,
  serverItems,
  readOnly,
  rutaItemId,
  onRefresh,
}: {
  categoria: MediaCategoria1A;
  serverItems: MediaArchivoListItem[];
  readOnly?: boolean;
  rutaItemId: number;
  onRefresh: () => void;
}) {
  const queue = useMediaCategoryQueue(categoria);
  const [preview, setPreview] = useState<MediaArchivoListItem | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const handleDelete = async (archivoId: number) => {
    if (!window.confirm("¿Eliminar este archivo?")) return;
    setDeletingId(archivoId);
    try {
      await deleteArchivo(archivoId);
      onRefresh();
    } finally {
      setDeletingId(null);
    }
  };

  const uploadPending = async () => {
    await queue.uploadAll(rutaItemId);
    queue.reset();
    onRefresh();
  };

  return (
    <Box>
      <Typography variant="subtitle2" sx={{ color: GLASS_COLORS.textPrimary, mb: 0.5 }}>
        {MEDIA_CATEGORY_LABELS[categoria]}{" "}
        <Typography component="span" variant="caption" sx={{ color: GLASS_COLORS.textMuted }}>
          {serverItems.length} / {MEDIA_CATEGORY_MAX[categoria]}
        </Typography>
      </Typography>
      <GalleryTiles items={serverItems} onOpen={setPreview} />
      {!readOnly ? (
        <>
          <MediaUploadSection
            categoria={categoria}
            items={queue.items}
            serverCount={serverItems.length}
            onAddFiles={(files, tipo) => queue.addFiles(files, tipo, serverItems.length)}
            onRemove={queue.removeItem}
            onRetry={(id) => {
              void queue.retryItem(id);
            }}
          />
          {queue.hasPendingUpload ? (
            <Button size="small" sx={{ mt: 1 }} onClick={() => void uploadPending()}>
              Subir archivos seleccionados
            </Button>
          ) : null}
        </>
      ) : null}
      {!readOnly ? (
        <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 1 }}>
          {serverItems.map((item) => (
            <Button
              key={item.archivo_id}
              size="small"
              color="inherit"
              disabled={deletingId === item.archivo_id}
              onClick={() => void handleDelete(item.archivo_id)}
            >
              Eliminar {item.original_filename}
            </Button>
          ))}
        </Stack>
      ) : null}
      <MediaPreviewDialog open={preview != null} item={preview} onClose={() => setPreview(null)} />
    </Box>
  );
}

export function ActuacionMediaGallery({ rutaItemId, readOnly = false, hideTitle = false }: Props) {
  const [data, setData] = useState<{ foto_acta: MediaArchivoListItem[]; foto_documentacion_local: MediaArchivoListItem[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  if (!rutaItemId) {
    return (
      <Typography variant="body2" sx={{ color: GLASS_COLORS.textMuted }}>
        No hay ítem de ruta asociado para archivos.
      </Typography>
    );
  }

  return (
    <Stack spacing={2}>
      {!hideTitle ? (
        <Typography variant="subtitle1" sx={{ color: GLASS_COLORS.textPrimary }}>
          Archivos de la actuación
        </Typography>
      ) : null}
      {error ? <Typography color="error">{error}</Typography> : null}
      <CategoryBlock
        categoria={MEDIA_CATEGORIA_FOTO_ACTA}
        serverItems={data?.foto_acta ?? []}
        readOnly={readOnly}
        rutaItemId={rutaItemId}
        onRefresh={load}
      />
      <CategoryBlock
        categoria={MEDIA_CATEGORIA_FOTO_DOCUMENTACION_LOCAL}
        serverItems={data?.foto_documentacion_local ?? []}
        readOnly={readOnly}
        rutaItemId={rutaItemId}
        onRefresh={load}
      />
    </Stack>
  );
}
