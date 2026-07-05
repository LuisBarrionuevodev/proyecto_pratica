import { Chip, Stack, Typography } from "@mui/material";
import type { DomicilioPendienteItem } from "../types";

function scoreLabel(score: number | null | undefined): string {
  if (score == null || Number.isNaN(Number(score))) return "—";
  return String(Math.round(Number(score)));
}

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
};

/** Chips read-only de clasificación compuesta (PR2/PR3). */
export function DomicilioClasificacionChips({ item, compact = false }: ChipRowProps) {
  const score = item.score_unificado ?? null;
  const hasClasificacion =
    item.nomenclatura_estado != null ||
    item.geocode_estado != null ||
    item.slice != null ||
    score != null;

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
      {item.nomenclatura_estado ? (
        <Chip size={size} label={item.nomenclatura_estado} variant="outlined" />
      ) : null}
      {item.geocode_estado ? (
        <Chip size={size} label={item.geocode_estado} variant="outlined" color="info" />
      ) : null}
      {score != null ? (
        <Chip
          size={size}
          label={`Score ${scoreLabel(score)}`}
          color={scoreColor(score)}
          variant="filled"
        />
      ) : null}
      {item.slice ? (
        <Chip size={size} label={item.slice} variant="outlined" color="secondary" />
      ) : null}
    </Stack>
  );
}

export function scoreUnificadoLabel(score: number | null | undefined): string {
  if (score == null || Number.isNaN(Number(score))) return "—";
  const n = Math.round(Number(score));
  if (n >= 90) return `${n} · OK`;
  if (n >= 60) return `${n} · Revisar`;
  return `${n} · Pendiente`;
}
