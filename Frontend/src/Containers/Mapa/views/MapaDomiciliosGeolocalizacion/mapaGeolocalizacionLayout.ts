import type { SxProps, Theme } from "@mui/material";

import { GLASS_COLORS } from "../../../../styles/GlassStyles";

/** Altura fija compartida: panel mapa + panel lista (PR6C.14c). */
export const MAP_GEO_PANEL_HEIGHT = 520;

/** Contenedor de panel mapa/lista con altura fija alineada. */
export const mapGeoPanelPaperSx: SxProps<Theme> = {
  height: MAP_GEO_PANEL_HEIGHT,
  minHeight: MAP_GEO_PANEL_HEIGHT,
  maxHeight: MAP_GEO_PANEL_HEIGHT,
  overflow: "hidden",
  display: "flex",
  flexDirection: "column",
  p: 0,
};

/** Contenedor scroll interno de la lista derecha. */
export const mapGeoListaScrollContainerSx: SxProps<Theme> = {
  flex: 1,
  minHeight: 0,
  height: "100%",
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
  boxSizing: "border-box",
};

/**
 * Padding inferior en el área scrolleable (solo body) para ver la última fila completa.
 */
export const mapGeoListaScrollSafeSx: SxProps<Theme> = {
  paddingBottom: 1.5,
  scrollPaddingBottom: "16px",
  boxSizing: "border-box",
};

/** Footer de paginación fijo, fuera del body scrolleable. */
export const mapGeoListaPaginationFooterSx: SxProps<Theme> = {
  flexShrink: 0,
  minHeight: 48,
  borderTop: "1px solid rgba(255,255,255,0.08)",
  backgroundColor: "rgba(30, 33, 39, 0.96)",
  display: "flex",
  alignItems: "center",
  px: 0.5,
  boxSizing: "border-box",
  "& .MuiTablePagination-root": {
    width: "100%",
    overflow: "visible",
    color: GLASS_COLORS.textSecondary,
  },
  "& .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows": {
    fontSize: "0.75rem",
  },
};

/**
 * Host flex lista → shell MRT: body scrolleable + paginación visible abajo (fuera del overflow del body).
 */
export const mapGeoListaMrtShellHostSx: SxProps<Theme> = {
  flex: 1,
  minHeight: 0,
  height: "100%",
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
  boxSizing: "border-box",
  "& > div": {
    flex: 1,
    minHeight: 0,
    height: "100%",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  "& > div > div:first-of-type": {
    flex: 1,
    minHeight: 0,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  "& > div > div:first-of-type > div": {
    flex: 1,
    minHeight: 0,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  "& .MuiPaper-root": {
    flex: 1,
    minHeight: 0,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    boxShadow: "none",
    backgroundImage: "none",
  },
};

/**
 * Overlay de edición en mapa: glass opaco (no transparencia mínima), desplazado a la derecha
 * para no tapar controles de zoom Leaflet (esquina superior derecha).
 */
export const mapEditOverlayGlassSx: SxProps<Theme> = {
  position: "absolute",
  top: 10,
  left: 56,
  right: 72,
  zIndex: 1000,
  backgroundColor: "rgba(30, 33, 39, 0.94)",
  backdropFilter: "blur(14px)",
  WebkitBackdropFilter: "blur(14px)",
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
  borderRadius: "12px",
  boxShadow: "0 4px 24px rgba(0, 0, 0, 0.35)",
  p: 1,
};
