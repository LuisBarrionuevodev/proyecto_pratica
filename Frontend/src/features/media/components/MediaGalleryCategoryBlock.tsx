import { memo } from "react";
import { Box, Stack, Typography } from "@mui/material";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import type { MediaCategoria } from "../mediaConstants";
import type { MediaArchivoListItem, MediaQueuedFile } from "../mediaTypes";
import { mediaArchivoListItemsArrayEqual } from "../utils/mediaThumbnailTileProps";
import { MediaGalleryServerThumbnails } from "./MediaGalleryServerThumbnails";
import { MediaUploadSection } from "./MediaUploadSection";

export type MediaGalleryCategoryConfig = {
  categoria: MediaCategoria;
  titulo: string;
  ejemplos: string;
  cupo: number;
};

type Props = {
  gallery: MediaGalleryCategoryConfig;
  serverItems: MediaArchivoListItem[];
  queueItems: MediaQueuedFile[];
  readOnly: boolean;
  deletingId: number | null;
  uploading: boolean;
  sessionActive: boolean;
  manualSave: boolean;
  pendingQueueTitle: string;
  pendingPhaseLabel: string;
  onOpenById: (archivoId: number) => void;
  onDeleteById?: (archivoId: number) => void;
  onAddFiles: (files: FileList | File[]) => void;
  onRemove: (localId: string) => void;
  onRetry?: (localId: string) => void;
};

function queueItemsRenderSignature(items: MediaQueuedFile[]): string {
  return items
    .map((x) => `${x.localId}:${x.phase}:${x.progressPct ?? 0}`)
    .join("|");
}

function MediaGalleryCategoryBlockInner({
  gallery,
  serverItems,
  queueItems,
  readOnly,
  deletingId,
  uploading,
  sessionActive,
  manualSave: _manualSave,
  pendingQueueTitle,
  pendingPhaseLabel,
  onOpenById,
  onDeleteById,
  onAddFiles,
  onRemove,
  onRetry,
}: Props) {
  const localPending = queueItems.filter((x) => x.phase !== "ready").length;
  const used = serverItems.length + localPending;
  const disabled = uploading || sessionActive;

  return (
    <Box sx={{ mb: 2 }}>
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
        <MediaGalleryServerThumbnails
          items={serverItems}
          deletingId={deletingId}
          readOnly={readOnly}
          onOpenById={onOpenById}
          onDeleteById={onDeleteById}
        />
      )}
      {!readOnly ? (
        <MediaUploadSection
          embedded
          categoria={gallery.categoria}
          items={queueItems}
          serverCount={serverItems.length}
          onAddFiles={onAddFiles}
          onRemove={onRemove}
          onRetry={onRetry}
          disabled={disabled}
          pendingQueueTitle={pendingQueueTitle}
          pendingPhaseLabel={pendingPhaseLabel}
        />
      ) : null}
    </Box>
  );
}

function propsAreEqual(prev: Props, next: Props): boolean {
  if (prev.readOnly !== next.readOnly) return false;
  if (prev.deletingId !== next.deletingId) return false;
  if (prev.uploading !== next.uploading) return false;
  if (prev.sessionActive !== next.sessionActive) return false;
  if (prev.manualSave !== next.manualSave) return false;
  if (prev.pendingQueueTitle !== next.pendingQueueTitle) return false;
  if (prev.pendingPhaseLabel !== next.pendingPhaseLabel) return false;
  if (prev.gallery.categoria !== next.gallery.categoria) return false;
  if (prev.onOpenById !== next.onOpenById) return false;
  if (prev.onDeleteById !== next.onDeleteById) return false;
  if (prev.onAddFiles !== next.onAddFiles) return false;
  if (prev.onRemove !== next.onRemove) return false;
  if (prev.onRetry !== next.onRetry) return false;
  if (!mediaArchivoListItemsArrayEqual(prev.serverItems, next.serverItems)) return false;
  return queueItemsRenderSignature(prev.queueItems) === queueItemsRenderSignature(next.queueItems);
}

export const MediaGalleryCategoryBlock = memo(MediaGalleryCategoryBlockInner, propsAreEqual);
