import { Typography } from "@mui/material";

import type { IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { buildRutaContextoLine } from "../utils/rutaResumenLabels";

export type RutaContextoLineProps = {
  ruta: IRutaTrabajo;
  /** Fragmento final opcional (ej. «En pool: 3»). */
  suffix?: string | null;
  /** Variante compacta para títulos de panel. */
  variant?: "default" | "compact";
};

/**
 * Línea contextual de ruta: Borrador · fecha · turno (+ sufijo opcional).
 */
export function RutaContextoLine({ ruta, suffix, variant = "default" }: RutaContextoLineProps) {
  const text = buildRutaContextoLine(ruta, suffix);
  return (
    <Typography
      component="span"
      data-testid="ruta-contexto-line"
      sx={{
        fontFamily: '"Tactic Sans", sans-serif',
        fontSize: variant === "compact" ? "0.72rem" : "0.8125rem",
        fontWeight: 600,
        color: GLASS_COLORS.textSecondary,
        lineHeight: 1.35,
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </Typography>
  );
}
