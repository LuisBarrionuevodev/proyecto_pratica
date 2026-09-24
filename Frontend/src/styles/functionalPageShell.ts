import type { SxProps, Theme } from "@mui/material";

/**
 * F3.8c — Unidad de `theme.spacing` entre la caja superior (tabs / filtros / slices) y el contenido principal
 * (tabla, grilla, panel). Valor `2` → 16px con el theme por defecto de MUI.
 */
export const FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING = 2;

/**
 * Shell estándar del área de contenido de vistas funcionales (baseline: `/cargarRelevamiento`).
 *
 * Unifica padding, gap y ritmo vertical bajo el breadcrumb del `AppLayout`, sin acoplarse a grillas ni filtros.
 */
export const functionalPageShellSx: SxProps<Theme> = {
  width: "100%",
  maxWidth: "100%",
  boxSizing: "border-box",
  minHeight: 0,
  p: { xs: 2, sm: 3 },
  display: "flex",
  flexDirection: "column",
  gap: FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING,
};
