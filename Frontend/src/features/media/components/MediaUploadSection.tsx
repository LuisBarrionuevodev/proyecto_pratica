import { useRef } from "react";
import { Box, Stack, Typography } from "@mui/material";
import { AppButton } from "../../../ui";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import {
  MEDIA_CATEGORY_HINTS,
  MEDIA_CATEGORY_LABELS,
  MEDIA_CATEGORY_MAX,
  type MediaCategoria1A,
} from "../mediaConstants";
import type { MediaQueuedFile } from "../mediaTypes";
import { MediaUploadQueue } from "./MediaUploadQueue";

type Props = {
  categoria: MediaCategoria1A;
  items: MediaQueuedFile[];
  serverCount?: number;
  onAddFiles: (files: FileList) => void;
  onRemove: (localId: string) => void;
  onRetry?: (localId: string) => void;
  disabled?: boolean;
  /** Solo botón y cola; el encabezado/contador lo muestra el padre (galería CRUD). */
  embedded?: boolean;
};

export function MediaUploadSection({
  categoria,
  items,
  serverCount = 0,
  onAddFiles,
  onRemove,
  onRetry,
  disabled,
  embedded = false,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const label = MEDIA_CATEGORY_LABELS[categoria];
  const hint = MEDIA_CATEGORY_HINTS[categoria];
  const max = MEDIA_CATEGORY_MAX[categoria];
  const localPending = items.filter((x) => x.phase !== "ready").length;
  const used = serverCount + localPending;

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
      <Stack spacing={1}>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="image/jpeg,image/png,image/webp,application/pdf"
          hidden
          onChange={(e) => {
            const files = e.target.files;
            if (files && files.length > 0) {
              onAddFiles(files);
            }
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
        <MediaUploadQueue items={items} onRemove={onRemove} onRetry={onRetry} disabled={disabled} />
      </Stack>
    </Box>
  );
}
