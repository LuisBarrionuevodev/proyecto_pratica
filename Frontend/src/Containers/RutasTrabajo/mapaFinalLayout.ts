/** Altura útil del mapa Leaflet en mapa final (viewport apilado vs lateral). */
export const MAPA_FINAL_MAP_HEIGHT_SX = {
  xs: "min(52vh, 440px)",
  md: "min(72vh, 680px)",
} as const;

/** Panel lateral de grupos/direcciones: scroll interno en móvil y desktop. */
export const MAPA_FINAL_RESUMEN_PANEL_SX = {
  flex: { xs: "1 1 auto", md: "0 0 360px" },
  width: { xs: "100%", md: "auto" },
  maxWidth: { xs: "100%", md: 440 },
  minWidth: { xs: 0, md: 300 },
  maxHeight: {
    xs: "min(52vh, 520px)",
    md: "min(72vh, 680px)",
  },
  minHeight: { xs: 200, md: 0 },
} as const;
