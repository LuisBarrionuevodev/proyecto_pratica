import { forwardRef } from "react";
import { Box, LinearProgress, Typography } from "@mui/material";
import { AppButton } from "../../../ui";
import { useDigitalizaTheme } from "../../../theme/DigitalizaThemeProvider";
import type { MediaQueuedFile } from "../mediaTypes";
import { mediaUploadProgressPanelSx } from "../mediaUploadProgressPanelStyles";
import { resolveMediaUploadPanelPhase } from "../utils/mediaUploadPanelVisibility";

type Props = {
  open: boolean;
  sessionActive: boolean;
  globalPct: number;
  items: MediaQueuedFile[];
  onRetry?: (localId: string) => void;
};

function countProgress(items: MediaQueuedFile[]): { done: number; total: number; current: number } {
  const total = items.length;
  const done = items.filter((x) => x.phase === "ready").length;
  const inFlight = items.some(
    (x) => x.phase === "preparing" || x.phase === "uploading" || x.phase === "verifying"
  );
  const current = Math.min(done + (inFlight ? 1 : 0), total);
  return { done, total, current };
}

/**
 * Panel sólido dentro del modal (sin Dialog ni position:fixed).
 * El contador N/Total es la fuente de verdad visual; la barra refleja archivos completados.
 */
export const MediaUploadProgress = forwardRef<HTMLElement, Props>(function MediaUploadProgress(
  { open, sessionActive, globalPct, items, onRetry },
  ref
) {
  const { mode, colors } = useDigitalizaTheme();
  if (!open || items.length === 0) return null;

  const { done, total, current } = countProgress(items);
  const inFlight = items.some(
    (x) => x.phase === "preparing" || x.phase === "uploading" || x.phase === "verifying"
  );
  const phase = resolveMediaUploadPanelPhase(sessionActive, items);
  const fileBasedPct = total > 0 ? Math.round((done / total) * 100) : 0;
  const barValue = phase === "uploading" ? Math.max(fileBasedPct, Math.min(100, globalPct)) : fileBasedPct;

  const textPrimary = colors.text.primary;
  const textMuted = colors.text.muted;
  const errorColor = "#d32f2f";

  let headline = "Subiendo fotos";
  let counterLine = `${current} / ${total}`;
  let preparandoLine: string | null = null;
  let detailLine = `Se guardaron ${done} fotos. Cargando la foto ${Math.min(done + 1, total)}…`;
  let warningLine: string | null = "No cierres esta pantalla.";

  if (phase === "success") {
    headline = "Fotos cargadas correctamente";
    counterLine = `${done} / ${total} · Carga finalizada`;
    detailLine = "";
    warningLine = null;
  } else if (phase === "interrupted") {
    headline = "Carga interrumpida";
    counterLine = `${done} / ${total}`;
    detailLine =
      "Se guardaron las fotos anteriores. Podés continuar cuando vuelva la conexión.";
    warningLine = null;
  } else if (phase === "uploading" && done === 0 && !inFlight) {
    counterLine = `0 / ${total}`;
    preparandoLine = "Preparando carga…";
    detailLine = "Se guardaron 0 fotos. Iniciando la foto 1…";
  } else if (done === 0 && current <= 1) {
    detailLine = `Preparando foto ${current} de ${total}…`;
  }

  const errorItem = items.find((x) => x.phase === "error");

  return (
    <Box
      ref={ref}
      component="section"
      data-testid="media-upload-progress-panel"
      aria-live="polite"
      aria-busy={phase === "uploading"}
      sx={{
        ...mediaUploadProgressPanelSx(mode),
        mb: 2,
        position: "relative",
        width: "100%",
        maxWidth: "100%",
      }}
    >
      <Typography variant="subtitle1" sx={{ color: textPrimary, fontWeight: 700 }}>
        {headline}
      </Typography>
      <Typography variant="h6" sx={{ color: textPrimary, fontWeight: 700, mt: 0.5, letterSpacing: 0.5 }}>
        {counterLine}
      </Typography>
      {warningLine ? (
        <Typography variant="body2" sx={{ color: textMuted, mt: 0.5 }}>
          {warningLine}
        </Typography>
      ) : null}
      {preparandoLine ? (
        <Typography variant="body2" sx={{ color: textMuted, mt: 0.5 }}>
          {preparandoLine}
        </Typography>
      ) : null}
      <LinearProgress
        variant="determinate"
        value={barValue}
        color={phase === "interrupted" ? "inherit" : "primary"}
        sx={{
          mt: 1.5,
          mb: 1,
          height: 10,
          borderRadius: 1,
          bgcolor: "action.hover",
          "& .MuiLinearProgress-bar": phase === "interrupted" ? { bgcolor: errorColor } : undefined,
        }}
      />
      {detailLine ? (
        <Typography variant="body2" sx={{ color: textMuted }}>
          {detailLine}
        </Typography>
      ) : null}
      {errorItem && onRetry ? (
        <Box sx={{ mt: 1.5, display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <Typography variant="caption" sx={{ color: errorColor }}>
            {errorItem.errorMessage ?? "Error al subir"}
          </Typography>
          <AppButton dsVariant="ghost" dsSize="sm" onClick={() => onRetry(errorItem.localId)}>
            Reintentar
          </AppButton>
        </Box>
      ) : null}
    </Box>
  );
});
