import { Chip, Stack, Typography } from "@mui/material";
import {
  labelGeocodeEstado,
  labelNomenclaturaEstado,
  labelScoreUnificado,
} from "../domicilioClasificacionLabels";
import type { DomicilioPendienteItem } from "../types";

function scoreColor(score: number | null | undefined): "success" | "warning" | "error" | "default" {
  if (score == null || Number.isNaN(Number(score))) return "default";
  const n = Number(score);
  if (n >= 90) return "success";
  if (n >= 60) return "warning";
  return "error";
}

type ChipRowProps = {
  item: DomicilioPendienteItem;
  compact?: boolean;
  /** Si false, el score va en columna aparte. */
  showScore?: boolean;
};

/** Chips read-only de clasificación compuesta (labels humanos). */
export function DomicilioClasificacionChips({
  item,
  compact = false,
  showScore = false,
}: ChipRowProps) {
  const nomenclaturaRaw = item.nomenclatura_estado ?? item.calle_status;
  const geocodeRaw = item.geocode_estado ?? item.geo_status;
  const score = item.score_unificado ?? null;
  const hasClasificacion = nomenclaturaRaw != null || geocodeRaw != null || (showScore && score != null);

  if (!hasClasificacion) {
    return (
      <Typography variant="body2" color="text.secondary">
        —
      </Typography>
    );
  }

  const size = compact ? "small" : "medium";

  return (
    <Stack direction="row" flexWrap="wrap" gap={0.5} useFlexGap>
      {nomenclaturaRaw ? (
        <Chip
          size={size}
          label={labelNomenclaturaEstado(String(nomenclaturaRaw))}
          variant="outlined"
        />
      ) : null}
      {geocodeRaw ? (
        <Chip
          size={size}
          label={labelGeocodeEstado(String(geocodeRaw))}
          variant="outlined"
          color="info"
        />
      ) : null}
      {showScore && score != null ? (
        <Chip
          size={size}
          label={labelScoreUnificado(score)}
          color={scoreColor(score)}
          variant="filled"
        />
      ) : null}
    </Stack>
  );
}

export function scoreUnificadoLabel(score: number | null | undefined): string {
  if (score == null || Number.isNaN(Number(score))) return "—";
  const n = Math.round(Number(score));
  const band = labelScoreUnificado(score);
  return band === "—" ? "—" : `${n} · ${band}`;
}
