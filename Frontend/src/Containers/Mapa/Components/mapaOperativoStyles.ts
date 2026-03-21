import type { SxProps, Theme } from "@mui/material";

import { glassCard, glassTabsHeaderPanelSx, GLASS_COLORS } from "../../../styles/GlassStyles";

/** Panel glass reutilizable (cabecera de modo, barras de filtros, resumen, contenedor de mapa). */
export const mapaOperativoGlassPanelSx: SxProps<Theme> = glassTabsHeaderPanelSx;

/** Superficie glass para el canvas Leaflet (sin padding interno en el borde del mapa). */
export const mapaOperativoSurfaceSx: SxProps<Theme> = {
  ...glassCard,
  p: 0,
  overflow: "hidden",
};

/** Barra de filtros / cabecera de datos con padding. */
export const mapaOperativoBarSx: SxProps<Theme> = {
  ...mapaOperativoGlassPanelSx,
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

/** Subcaja dentro del panel lateral (separación visual entre bloques). */
export const mapaOperativoInnerCardSx: SxProps<Theme> = {
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  borderRadius: "12px",
  p: 1.75,
  backgroundColor: GLASS_COLORS.hoverBg,
  backdropFilter: "blur(10px)",
  WebkitBackdropFilter: "blur(10px)",
};
