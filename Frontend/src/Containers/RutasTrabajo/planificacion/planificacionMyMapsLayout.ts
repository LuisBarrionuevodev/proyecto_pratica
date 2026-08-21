import type { SxProps, Theme } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import {
  planificacionPanelColumnSx,
  rutasInstitutionalPanelPaperSx,
  rutasInstitutionalScrollSx,
} from "../styles/institutionalVisual";

/** Altura compartida panel lateral + mapa (OPER-RUTA.7C). */
export const PLANIFICACION_MY_MAPS_HEIGHT = "min(82vh, 880px)";

/** Shell lateral único: filtros + tabs + lista + acciones. */
export const planificacionSidebarShellSx: SxProps<Theme> = {
  ...rutasInstitutionalPanelPaperSx,
  ...planificacionPanelColumnSx,
  p: 1.5,
  gap: 1,
  height: "100%",
  minHeight: 480,
  maxHeight: PLANIFICACION_MY_MAPS_HEIGHT,
};

/** Área scrolleable del contenido del tab activo. */
export const planificacionSidebarTabBodySx: SxProps<Theme> = {
  flex: "1 1 0",
  minHeight: 0,
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
};

/** Lista interna dentro de un tab (scroll + safe area). */
export const planificacionSidebarListViewportSx: SxProps<Theme> = {
  flex: "1 1 0",
  minHeight: 0,
  overflowY: "auto",
  overflowX: "hidden",
  paddingBottom: 1.5,
  scrollPaddingBottom: "16px",
  boxSizing: "border-box",
  ...rutasInstitutionalScrollSx,
};

/** Barra de filtros compacta bajo el header del sidebar. */
export const planificacionFiltrosBarSx: SxProps<Theme> = {
  flexShrink: 0,
  display: "flex",
  flexDirection: "column",
  gap: 0.75,
  pb: 0.75,
  borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
};

/** Chips de filtros activos. */
export const planificacionActiveFiltersRowSx: SxProps<Theme> = {
  display: "flex",
  flexWrap: "wrap",
  gap: 0.5,
  alignItems: "center",
  minHeight: 24,
};

/** Footer fijo con acciones rápidas. */
export const planificacionSidebarFooterSx: SxProps<Theme> = {
  flexShrink: 0,
  pt: 0.75,
  borderTop: `1px solid ${GLASS_COLORS.borderLight}`,
};
