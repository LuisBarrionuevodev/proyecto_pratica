import { useRef, useState } from "react";
import { Box, MenuItem, Stack, Typography } from "@mui/material";
import { AppSelect } from "../../../ui";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import {
  MEDIA_CATEGORY_LABELS,
  MEDIA_CATEGORY_MAX,
  TIPOS_DOCUMENTO_FOTO_ACTA,
  TIPOS_DOCUMENTO_FOTO_LOCAL,
  type MediaCategoria1A,
} from "../mediaConstants";
import type { MediaQueuedFile } from "../mediaTypes";
import { MediaUploadQueue } from "./MediaUploadQueue";

type Props = {
  categoria: MediaCategoria1A;
  items: MediaQueuedFile[];
  serverCount?: number;
  onAddFiles: (files: FileList, tipoDocumento: string | null) => void;
  onRemove: (localId: string) => void;
  onRetry?: (localId: string) => void;
  disabled?: boolean;
};

export function MediaUploadSection({
  categoria,
  items,
  serverCount = 0,
  onAddFiles,
  onRemove,
  onRetry,
  disabled,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [tipoDocumento, setTipoDocumento] = useState<string>("");
  const label = MEDIA_CATEGORY_LABELS[categoria];
  const max = MEDIA_CATEGORY_MAX[categoria];
  const localPending = items.filter((x) => x.phase !== "ready").length;
  const used = serverCount + localPending;

  const tipoOpts =
    categoria === "FOTO_ACTA" ? TIPOS_DOCUMENTO_FOTO_ACTA : TIPOS_DOCUMENTO_FOTO_LOCAL;

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="subtitle2" sx={{ color: GLASS_COLORS.textPrimary }}>
          {label}
        </Typography>
        <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted }}>
          {used} / {max}
        </Typography>
      </Stack>
      <Stack spacing={1}>
        <AppSelect
          appearance="glass"
          label="Tipo de documento (opcional)"
          value={tipoDocumento}
          onChange={(e) => setTipoDocumento(e.target.value)}
          fullWidth
          disabled={disabled}
        >
          <MenuItem value="">
            <em>Sin especificar</em>
          </MenuItem>
          {tipoOpts.map((t) => (
            <MenuItem key={t} value={t}>
              {t.replace(/_/g, " ")}
            </MenuItem>
          ))}
        </AppSelect>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="image/jpeg,image/png,image/webp,application/pdf"
          hidden
          onChange={(e) => {
            const files = e.target.files;
            if (files && files.length > 0) {
              onAddFiles(files, tipoDocumento || null);
            }
            e.target.value = "";
          }}
        />
        <Typography
          component="button"
          type="button"
          variant="body2"
          onClick={() => inputRef.current?.click()}
          disabled={disabled || used >= max}
          sx={{
            textAlign: "left",
            border: "none",
            background: "none",
            cursor: disabled || used >= max ? "not-allowed" : "pointer",
            color: "primary.main",
            p: 0,
          }}
        >
          Seleccionar archivos
        </Typography>
        <MediaUploadQueue items={items} onRemove={onRemove} onRetry={onRetry} disabled={disabled} />
      </Stack>
    </Box>
  );
}
