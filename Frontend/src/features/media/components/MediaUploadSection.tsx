import { useRef } from "react";
import { Box, ImageList, Stack, Typography } from "@mui/material";
import { AppButton } from "../../../ui";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import {
  MEDIA_CATEGORY_HINTS,
  MEDIA_CATEGORY_LABELS,
  MEDIA_CATEGORY_MAX,
  mediaAcceptAttributeForCategoria,
  type MediaCategoria,
} from "../mediaConstants";
import type { MediaArchivoListItem, MediaQueuedFile } from "../mediaTypes";
import { MediaThumbnailTile } from "./MediaThumbnailTile";
import { safeFilesFromFileList } from "../utils/safeFileSelection";
import { MediaUploadQueue } from "./MediaUploadQueue";

type Props = {
  categoria: MediaCategoria;
  items: MediaQueuedFile[];
  serverCount?: number;
  /** Miniaturas READY del servidor (solo lectura en flujo de continuación). */
  readyServerItems?: MediaArchivoListItem[];
  onAddFiles: (files: FileList | File[]) => void;
  onRemove: (localId: string) => void;
  onRetry?: (localId: string) => void;
  disabled?: boolean;
  /** Solo botón y cola; el encabezado/contador lo muestra el padre (galería CRUD). */
  embedded?: boolean;
  /** Etiqueta de cola local (Inspector: “fotos” en lugar de “evidencias”). */
  pendingQueueTitle?: string;
  pendingPhaseLabel?: string;
};

export function MediaUploadSection({
  categoria,
  items,
  serverCount = 0,
  readyServerItems = [],
  onAddFiles,
  onRemove,
  onRetry,
  disabled,
  embedded = false,
  pendingQueueTitle = "Fotos pendientes de carga",
  pendingPhaseLabel = "Pendiente de carga",
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const label = MEDIA_CATEGORY_LABELS[categoria];
  const hint = MEDIA_CATEGORY_HINTS[categoria];
  const max = MEDIA_CATEGORY_MAX[categoria];
  const localPending = items.filter((x) => x.phase !== "ready").length;
  const readyCount = readyServerItems.length > 0 ? readyServerItems.length : serverCount;
  const used = readyCount + localPending;

  const handleFileChange = (files: FileList | null) => {
    const list = safeFilesFromFileList(files);
    if (list.length === 0) return;
    try {
      onAddFiles(list);
    } catch (err) {
      console.error("Error al agregar archivos a la cola:", err);
    }
  };

  return (
    <Box>
      {!embedded ? (
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 0.5 }}>
          <Box>
            <Typography variant="subtitle2" sx={{ color: GLASS_COLORS.textPrimary }}>
              {label}
            </Typography>
            <Typography variant="body2" sx={{ color: GLASS_COLORS.textMuted, fontStyle: "italic", mt: 0.25 }}>
              {hint}
            </Typography>
          </Box>
          <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted, flexShrink: 0, ml: 1 }}>
            {used} / {max}
          </Typography>
        </Stack>
      ) : null}
      {readyServerItems.length > 0 ? (
        <ImageList cols={3} gap={8} sx={{ m: 0, mb: 1 }}>
          {readyServerItems.map((item) => (
            <MediaThumbnailTile key={item.archivo_id} item={item} onOpen={() => undefined} />
          ))}
        </ImageList>
      ) : null}
      <Stack spacing={1}>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={mediaAcceptAttributeForCategoria(categoria)}
          hidden
          onChange={(e) => {
            handleFileChange(e.target.files);
            e.target.value = "";
          }}
        />
        <AppButton
          dsVariant="primary"
          dsSize="sm"
          onClick={() => inputRef.current?.click()}
          disabled={disabled || used >= max}
        >
          Seleccionar archivos
        </AppButton>
        {localPending > 0 ? (
          <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted }}>
            {pendingQueueTitle} · {localPending}
          </Typography>
        ) : null}
        <MediaUploadQueue
          items={items}
          onRemove={onRemove}
          onRetry={onRetry}
          disabled={disabled}
          pendingPhaseLabel={pendingPhaseLabel}
        />
      </Stack>
    </Box>
  );
}
