import type { SxProps, Theme } from "@mui/material";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import {
  planificacionPanelColumnSx,
  rutasInstitutionalPanelPaperSx,
  rutasInstitutionalScrollSx,
} from "../styles/institutionalVisual";

/**
 * Reserva vertical aproximada: shell app + header institucional + header compacto + pool strip + paddings.
 * OPER-RUTA.7C.3: main area ocupa el resto del viewport.
 */
export const PLANIFICACION_CHROME_OFFSET_PX = 280;

/** Altura del bloque panel + mapa (flex child o calc). */
export const PLANIFICACION_MAIN_AREA_MIN_HEIGHT_PX = 580;

export const planificacionMainAreaSx: SxProps<Theme> = {
  flex: "1 1 auto",
  minHeight: PLANIFICACION_MAIN_AREA_MIN_HEIGHT_PX,
  height: `max(${PLANIFICACION_MAIN_AREA_MIN_HEIGHT_PX}px, calc(100vh - ${PLANIFICACION_CHROME_OFFSET_PX}px))`,
  minWidth: 0,
  alignItems: "stretch",
};

/** @deprecated Usar planificacionMainAreaSx; mantener alias para mapa interno. */
export const PLANIFICACION_MY_MAPS_HEIGHT = "100%";

/** Shell lateral único: filtros + tabs + lista + acciones. */
export const planificacionSidebarShellSx: SxProps<Theme> = {
  ...rutasInstitutionalPanelPaperSx,
  ...planificacionPanelColumnSx,
  p: 1.5,
  gap: 1,
  height: "100%",
  minHeight: 0,
  display: "flex",
  flexDirection: "column",
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
