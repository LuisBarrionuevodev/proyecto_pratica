import type { SxProps, Theme } from "@mui/material";

import {
  GLASS_COLORS,
  moduleContentPanelPaperSx,
  moduleFiltersSurfaceSx,
  moduleHeroCardSx,
} from "../../../styles/GlassStyles";

/**
 * Panel lateral resumen: mismo preset que bloques de contenido F3.8c (Completar / bandejas).
 */
export const mapaOperativoGlassPanelSx: SxProps<Theme> = {
  ...moduleContentPanelPaperSx,
};

/** Barra de filtros: superficie estándar de filtros (sin padding extra respecto al sistema). */
export const mapaOperativoBarSx: SxProps<Theme> = {
  ...moduleFiltersSurfaceSx,
};

/**
 * Marco del canvas Leaflet: alineado a `glassCard` (borde medio, radio 16px, sin sombra fuerte).
 */
export const mapaOperativoSurfaceSx: SxProps<Theme> = {
  backgroundColor: GLASS_COLORS.cardBg,
  backdropFilter: "blur(14px)",
  WebkitBackdropFilter: "blur(14px)",
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
  borderRadius: "16px",
  boxShadow: "none",
  p: 0,
  overflow: "hidden",
};

/**
 * Ajustes mínimos de ancho para campos; el aspecto glass lo define `appearance="glass"` en App*.
 */
export const mapaOperativoFieldSx: SxProps<Theme> = {
  minWidth: { xs: "100%", sm: 160 },
  "& .MuiInputLabel-root": {
    fontFamily: '"Tactic Sans", sans-serif',
  },
  "& .MuiOutlinedInput-input": {
    fontFamily: '"Tactic Sans", sans-serif',
  },
  "& .MuiSelect-select": {
    fontFamily: '"Tactic Sans", sans-serif',
  },
};

/** Texto secundario sobre fondos glass. */
export const mapaOperativoCaptionSx: SxProps<Theme> = {
  color: GLASS_COLORS.textMuted,
  fontFamily: '"Tactic Sans", sans-serif',
};

/** Subcaja dentro del panel lateral (métricas / leyenda): mismo baseline que `moduleHeroCardSx`. */
export const mapaOperativoInnerCardSx: SxProps<Theme> = {
  ...moduleHeroCardSx,
  p: 1.75,
};
