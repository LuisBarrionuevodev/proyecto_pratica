import { Box, Button, LinearProgress, Stack, Typography } from "@mui/material";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import type { MediaQueuedFile } from "../mediaTypes";

const phaseLabel: Record<MediaQueuedFile["phase"], string> = {
  pending: "Pendiente",
  preparing: "Preparando",
  uploading: "Subiendo",
  verifying: "Verificando",
  ready: "Listo",
  error: "Error",
};

type Props = {
  items: MediaQueuedFile[];
  onRemove: (localId: string) => void;
  onRetry?: (localId: string) => void;
  disabled?: boolean;
};

export function MediaUploadQueue({ items, onRemove, onRetry, disabled }: Props) {
  if (items.length === 0) return null;
  return (
    <Stack spacing={1} sx={{ mt: 1 }}>
      {items.map((item) => (
        <Box
          key={item.localId}
          sx={{
            display: "flex",
            gap: 1,
            alignItems: "flex-start",
            p: 1,
            borderRadius: 1,
            border: `1px solid ${GLASS_COLORS.borderLight}`,
          }}
        >
          <Box sx={{ width: 48, height: 48, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
            {item.previewUrl ? (
              <img
                src={item.previewUrl}
                alt=""
                style={{ width: 48, height: 48, objectFit: "cover", borderRadius: 4 }}
              />
            ) : (
              <PictureAsPdfIcon sx={{ color: GLASS_COLORS.textSecondary }} />
            )}
          </Box>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="body2" noWrap sx={{ color: GLASS_COLORS.textPrimary }}>
              {item.file.name}
            </Typography>
            <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted }}>
              {(item.file.size / 1024).toFixed(0)} KB · {phaseLabel[item.phase]}
              {item.phase === "uploading" ? ` ${item.progressPct}%` : ""}
            </Typography>
            {item.phase === "uploading" ? (
              <LinearProgress variant="determinate" value={item.progressPct} sx={{ mt: 0.5 }} />
            ) : null}
            {item.errorMessage ? (
              <Typography variant="caption" color="error" display="block">
                {item.errorMessage}
              </Typography>
            ) : null}
          </Box>
          <Stack direction="row" spacing={0.5}>
            {item.phase === "error" && onRetry ? (
              <Button size="small" onClick={() => onRetry(item.localId)} disabled={disabled}>
                Reintentar
              </Button>
            ) : null}
            {item.phase !== "uploading" && item.phase !== "verifying" ? (
              <Button size="small" color="inherit" onClick={() => onRemove(item.localId)} disabled={disabled}>
                Quitar
              </Button>
            ) : null}
          </Stack>
        </Box>
      ))}
    </Stack>
  );
}
