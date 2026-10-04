import {
  Box,
  Dialog,
  LinearProgress,
  Stack,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { AppButton } from "../../../ui";
import { useDigitalizaTheme } from "../../../theme/DigitalizaThemeProvider";
import type { MediaQueuedFile } from "../mediaTypes";
import {
  mediaUploadProgressDialogPaperSx,
  mediaUploadProgressPanelSx,
} from "../mediaUploadProgressPanelStyles";

const phaseLabel: Record<MediaQueuedFile["phase"], string> = {
  pending: "Pendiente",
  preparing: "Preparando",
  uploading: "Subiendo",
  verifying: "Verificando",
  ready: "Listo",
  error: "Error al subir",
};

type Props = {
  open: boolean;
  globalPct: number;
  items: MediaQueuedFile[];
  onRetry?: (localId: string) => void;
};

export function MediaUploadProgress({ open, globalPct, items, onRetry }: Props) {
  const theme = useTheme();
  const { mode, colors } = useDigitalizaTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  if (!open) return null;
  const displayItems = items;
  const total = displayItems.length;
  const done = displayItems.filter((x) => x.phase === "ready").length;
  const inFlight = displayItems.some(
    (x) => x.phase === "preparing" || x.phase === "uploading" || x.phase === "verifying"
  );

  const panelSx = mediaUploadProgressPanelSx(mode);
  const textPrimary = colors.text.primary;
  const textMuted = colors.text.muted;
  const border = colors.border.default;

  return (
    <Dialog
      open={open}
      fullScreen={fullScreen}
      maxWidth="sm"
      fullWidth
      slotProps={{
        paper: {
          sx: mediaUploadProgressDialogPaperSx(mode),
        },
      }}
    >
      <Box sx={panelSx}>
        <Typography variant="h6" sx={{ color: textPrimary, mb: 1 }}>
          Subiendo evidencia
        </Typography>
        <Typography variant="body2" sx={{ color: textMuted, mb: 1 }}>
          Subiendo {Math.min(done + (inFlight ? 1 : 0), total)} de {total} archivos
        </Typography>
        <LinearProgress
          variant="determinate"
          value={globalPct}
          color="primary"
          sx={{ mb: 2, height: 8, borderRadius: 1 }}
        />
        <Stack spacing={1} sx={{ maxHeight: fullScreen ? "60vh" : 320, overflow: "auto" }}>
          {displayItems.map((item) => (
            <Box
              key={item.localId}
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 1,
                py: 0.5,
                borderBottom: `1px solid ${border}`,
              }}
            >
              <Box sx={{ minWidth: 0, flex: 1 }}>
                <Typography variant="body2" noWrap sx={{ color: textPrimary }}>
                  {item.file.name}
                </Typography>
                <Typography variant="caption" sx={{ color: textMuted }}>
                  {phaseLabel[item.phase]}
                  {item.phase === "uploading" ? ` ${item.progressPct}%` : ""}
                </Typography>
                {item.phase === "error" && item.errorMessage ? (
                  <Typography variant="caption" color="error" display="block">
                    {item.errorMessage}
                  </Typography>
                ) : null}
              </Box>
              {item.phase === "error" && onRetry ? (
                <AppButton dsVariant="ghost" dsSize="sm" onClick={() => onRetry(item.localId)}>
                  Reintentar
                </AppButton>
              ) : null}
            </Box>
          ))}
        </Stack>
      </Box>
    </Dialog>
  );
}
