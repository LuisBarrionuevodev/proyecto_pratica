import { Typography } from "@mui/material";

import { GLASS_COLORS } from "../../../../styles/GlassStyles";
import {
  buildEstablecimientoSecundario,
  type EstablecimientoDiscriminadores,
} from "../utils/iniciadorDisplay";

const tactic = '"Tactic Sans", sans-serif' as const;

export type EstablecimientoSecundarioLineProps = {
  item: EstablecimientoDiscriminadores;
  /** Tamaño de fuente (rem); default compacto para cards. */
  fontSize?: string;
};

/**
 * Línea discreta con nombre fantasía / ángulo esquina del relevamiento (solo Ruta de Trabajo).
 */
export function EstablecimientoSecundarioLine({
  item,
  fontSize = "0.66rem",
}: EstablecimientoSecundarioLineProps) {
  const line = buildEstablecimientoSecundario(item);
  if (!line) return null;

  return (
    <Typography
      sx={{
        fontFamily: tactic,
        fontSize,
        fontWeight: 500,
        lineHeight: 1.28,
        color: GLASS_COLORS.textMuted,
        wordBreak: "break-word",
      }}
    >
      {line}
    </Typography>
  );
}
