import type { SxProps, Theme } from "@mui/material";

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
  gap: 2,
};
