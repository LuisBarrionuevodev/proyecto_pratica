import type { SxProps, Theme } from "@mui/material";

import { GLASS_COLORS } from "./GlassStyles";

/**
 * Marco estándar del viewport de datos (Glide, tablas envueltas, etc.).
 * Baseline visual: `/cargarRelevamiento` — borde glass liviano, sin sombra MUI ni gradiente de relleno.
 */
export const dataViewportFrameSx: SxProps<Theme> = {
  width: "100%",
  minWidth: 0,
  alignSelf: "stretch",
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  borderRadius: "8px",
  overflow: "hidden",
  backgroundColor: "transparent",
  backgroundImage: "none",
  maxWidth: "100%",
  maxHeight: "100%",
};
