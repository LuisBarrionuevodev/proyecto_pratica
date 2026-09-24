import { Typography } from "@mui/material";

import { formatOperativoPeriodoLabel } from "../utils/dateRange";
import { GLASS_COLORS } from "../styles/GlassStyles";

type OperativoPeriodoLabelProps = {
  desde: string;
  hasta: string;
};

/** Muestra el rango operativo activo (Dashboard / Mapa) en formato legible. */
export function OperativoPeriodoLabel({ desde, hasta }: OperativoPeriodoLabelProps) {
  if (!desde?.trim() || !hasta?.trim()) return null;

  return (
    <Typography
      variant="body2"
      sx={{
        color: GLASS_COLORS.textMuted,
        fontFamily: '"Tactic Sans", sans-serif',
        letterSpacing: "0.01em",
      }}
    >
      Período operativo{" "}
      <Typography
        component="span"
        variant="body2"
        sx={{ fontWeight: 600, color: GLASS_COLORS.textPrimary, fontFamily: "inherit" }}
      >
        {formatOperativoPeriodoLabel(desde, hasta)}
      </Typography>
    </Typography>
  );
}
