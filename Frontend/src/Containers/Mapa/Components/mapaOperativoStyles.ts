import type { SxProps, Theme } from "@mui/material";

import { GLASS_COLORS, moduleFiltersSurfaceSx } from "../../../styles/GlassStyles";

const MAPA_OPERATIVO_PANEL_PAD = 2;

/**
 * Panel modo / resumen lateral: misma superficie glass liviana que filtros/slices del resto del sistema (F3.8c).
 */
export const mapaOperativoGlassPanelSx: SxProps<Theme> = {
  ...moduleFiltersSurfaceSx,
  p: MAPA_OPERATIVO_PANEL_PAD,
};

/** Barra de filtros unificados (Mapa operativo). */
export const mapaOperativoBarSx: SxProps<Theme> = {
  ...moduleFiltersSurfaceSx,
  p: MAPA_OPERATIVO_PANEL_PAD,
};

/**
 * Marco del canvas Leaflet: fondo/borde institucional, sin sombra tipo “card” Material.
 */
export const mapaOperativoSurfaceSx: SxProps<Theme> = {
  backgroundColor: GLASS_COLORS.cardBg,
  backdropFilter: "blur(10px)",
  WebkitBackdropFilter: "blur(10px)",
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  borderRadius: "12px",
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

/** Subcaja dentro del panel lateral (bloques de métricas). */
export const mapaOperativoInnerCardSx: SxProps<Theme> = {
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  borderRadius: "12px",
  p: 1.75,
  backgroundColor: "rgba(255, 255, 255, 0.035)",
  backdropFilter: "blur(10px)",
  WebkitBackdropFilter: "blur(10px)",
  boxShadow: "none",
};
