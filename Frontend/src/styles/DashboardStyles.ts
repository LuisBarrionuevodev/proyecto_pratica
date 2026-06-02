import { GLASS_COLORS } from "./GlassStyles";

/** Superficie glass compartida para KPI y ChartCard del dashboard (D1b). */
export const dashboardGlassCardSx = {
  backgroundColor: "rgba(255, 255, 255, 0.035)",
  backdropFilter: "blur(10px)",
  WebkitBackdropFilter: "blur(10px)",
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  borderRadius: "12px",
  boxShadow: "none",
  boxSizing: "border-box",
  height: "auto",
} as const;

/** Sección del dashboard: bloque integrado (título + contenido). */
export const dashboardSectionSurfaceSx = {
  backgroundColor: "rgba(255, 255, 255, 0.028)",
  backdropFilter: "blur(10px)",
  WebkitBackdropFilter: "blur(10px)",
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  borderRadius: "12px",
  boxShadow: "none",
  overflow: "hidden",
} as const;

export const dashboardSectionHeaderSx = {
  px: 2,
  pt: 1.25,
  pb: 1,
  borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
  backgroundColor: "rgba(255,255,255,0.02)",
} as const;

export const dashboardSectionBodySx = {
  p: { xs: 1.5, sm: 2 },
} as const;

export const dashboardCardTitleSx = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontWeight: 600,
  fontSize: "1rem",
  lineHeight: 1.35,
  color: GLASS_COLORS.textPrimary,
} as const;

export const dashboardKpiValueSx = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontWeight: 700,
  fontSize: "1.75rem",
  lineHeight: 1.15,
  color: GLASS_COLORS.textPrimary,
} as const;

export const dashboardKpiValueCompactSx = {
  ...dashboardKpiValueSx,
  fontSize: "1.45rem",
} as const;

export const dashboardKpiLabelSx = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontWeight: 600,
  fontSize: "0.8125rem",
  color: GLASS_COLORS.textSecondary,
} as const;

export const dashboardEmptyStateSx = {
  minHeight: 200,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontFamily: '"Tactic Sans", sans-serif',
  fontSize: "0.8125rem",
  color: GLASS_COLORS.textSecondary,
  textAlign: "center",
  px: 2,
} as const;

/** Empty state para rankings / bloques pequeños (D1d.2-hotfix). */
export const dashboardEmptyStateCompactSx = {
  minHeight: 72,
  py: 1.5,
  px: 1.5,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontFamily: '"Tactic Sans", sans-serif',
  fontSize: "0.8125rem",
  color: GLASS_COLORS.textSecondary,
  textAlign: "center",
} as const;

export const ChartStyle = {
  fontFamily: '"Tactic Sans", sans-serif',
  "&& .MuiChartsAxis-line": {
    stroke: GLASS_COLORS.borderMedium,
  },
  "&& .MuiChartsAxis-tickLabel": {
    fill: GLASS_COLORS.textSecondary,
    textOverflow: "unset",
    whiteSpace: "normal",
    overflow: "visible",
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: "0.75rem",
  },
  "&& .MuiChartsLegend-root": {
    color: GLASS_COLORS.textPrimary,
    fontSize: "0.8125rem",
    fontWeight: 500,
    fontFamily: '"Tactic Sans", sans-serif',
  },
} as const;

export const dashboardGlassTableSx = {
  "& .MuiTableCell-root": {
    borderColor: GLASS_COLORS.borderLight,
    color: GLASS_COLORS.textPrimary,
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: "0.8125rem",
  },
  "& .MuiTableCell-head": {
    fontWeight: 700,
    color: GLASS_COLORS.textSecondary,
    backgroundColor: "rgba(255,255,255,0.03)",
  },
} as const;
