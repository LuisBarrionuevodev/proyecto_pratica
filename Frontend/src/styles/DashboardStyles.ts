import { GLASS_COLORS } from "./GlassStyles";
import { FONT_FAMILY_UI } from "../theme/typography";
import { CSS_VAR_NAMES } from "../theme/applyCssVariables";

const analyticsCardBg = `var(${CSS_VAR_NAMES.surfaceAnalyticsCard})`;
const dashboardGlassBg = `var(${CSS_VAR_NAMES.surfaceDashboardGlassCard})`;
const dashboardSectionBg = `var(${CSS_VAR_NAMES.surfaceDashboardSection})`;
const dashboardSectionHeaderBg = `var(${CSS_VAR_NAMES.surfaceDashboardSectionHeader})`;
const chartGridStroke = `var(${CSS_VAR_NAMES.chartGrid})`;

/** Superficie glass compartida para KPI y ChartCard del dashboard (D1b). */
export const dashboardGlassCardSx = {
  backgroundColor: dashboardGlassBg,
  backdropFilter: "blur(10px)",
  WebkitBackdropFilter: "blur(10px)",
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  borderRadius: "12px",
  boxShadow: "none",
  boxSizing: "border-box",
  height: "auto",
} as const;

/** Card analytics dark (D1d.11-hotfix) — inspirada en MUI Dashboard Template. */
export const dashboardAnalyticsCardSx = {
  backgroundColor: analyticsCardBg,
  backdropFilter: "blur(12px)",
  WebkitBackdropFilter: "blur(12px)",
  border: `1px solid ${GLASS_COLORS.borderLight}`,
  borderRadius: "10px",
  boxShadow: "0 1px 2px rgba(0,0,0,0.24)",
  boxSizing: "border-box",
  transition: "border-color 0.2s ease, box-shadow 0.2s ease",
  "&:hover": {
    borderColor: GLASS_COLORS.borderMedium,
    boxShadow: "0 4px 14px rgba(0,0,0,0.28)",
  },
} as const;

export const DASHBOARD_KPI_CARD_MIN_HEIGHT = 108;

/** Ajustes mínimos de tabs de período (base: ``moduleSlicesTabsSx`` / slices Comprobación). */
export const dashboardPeriodTabsSx = {
  flexShrink: 0,
  "& .MuiTab-root": {
    minWidth: { xs: 72, sm: 88 },
    px: { xs: 1.25, sm: 2 },
  },
  "& .MuiTabs-indicator": {
    height: 3,
    borderRadius: "2px",
  },
} as const;

/** Sección del dashboard: bloque integrado (título + contenido). */
export const dashboardSectionSurfaceSx = {
  backgroundColor: dashboardSectionBg,
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
  backgroundColor: dashboardSectionHeaderBg,
} as const;

export const dashboardSectionBodySx = {
  p: { xs: 1.5, sm: 2 },
} as const;

export const dashboardCardTitleSx = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 600,
  fontSize: "1rem",
  lineHeight: 1.35,
  color: GLASS_COLORS.textPrimary,
} as const;

export const dashboardKpiValueSx = {
  fontFamily: FONT_FAMILY_UI,
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
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 600,
  fontSize: "0.8125rem",
  color: GLASS_COLORS.textSecondary,
} as const;

/** KPI analytics (D1d.11): etiqueta superior, número dominante. */
export const dashboardAnalyticsKpiLabelSx = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 700,
  fontSize: "0.7rem",
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  color: GLASS_COLORS.textPrimary,
  lineHeight: 1.35,
  mb: 0.75,
} as const;

export const dashboardAnalyticsKpiValueSx = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 700,
  fontSize: { xs: "1.65rem", sm: "1.85rem" },
  lineHeight: 1.1,
  color: GLASS_COLORS.textPrimary,
} as const;

export const dashboardAnalyticsChartTitleSx = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 700,
  fontSize: "0.875rem",
  lineHeight: 1.35,
  color: GLASS_COLORS.textPrimary,
  mb: 1,
} as const;

/** Leyendas y etiquetas principales en rankings / donuts. */
export const dashboardLegendLabelSx = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 700,
  fontSize: "0.75rem",
  color: GLASS_COLORS.textPrimary,
} as const;

export const dashboardEmptyStateSx = {
  minHeight: 200,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontFamily: FONT_FAMILY_UI,
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
  fontFamily: FONT_FAMILY_UI,
  fontSize: "0.8125rem",
  color: GLASS_COLORS.textSecondary,
  textAlign: "center",
} as const;

export const ChartStyle = {
  fontFamily: FONT_FAMILY_UI,
  "&& .MuiChartsAxis-line": {
    stroke: GLASS_COLORS.borderMedium,
  },
  "&& .MuiChartsAxis-tick": {
    stroke: GLASS_COLORS.borderLight,
  },
  "&& .MuiChartsAxis-tickLabel": {
    fill: GLASS_COLORS.textPrimary,
    textOverflow: "unset",
    whiteSpace: "normal",
    overflow: "visible",
    fontFamily: FONT_FAMILY_UI,
    fontSize: "0.72rem",
    fontWeight: 700,
  },
  "&& .MuiChartsGrid-line": {
    stroke: chartGridStroke,
    strokeDasharray: "4 4",
  },
  "&& .MuiChartsLegend-root": {
    color: GLASS_COLORS.textPrimary,
    fontSize: "0.8125rem",
    fontWeight: 500,
    fontFamily: FONT_FAMILY_UI,
  },
  "&& .MuiBarLabel-root": {
    fill: GLASS_COLORS.textPrimary,
    fontFamily: FONT_FAMILY_UI,
    fontSize: "0.7rem",
    fontWeight: 600,
  },
} as const;

export const dashboardGlassTableSx = {
  "& .MuiTableCell-root": {
    borderColor: GLASS_COLORS.borderLight,
    color: GLASS_COLORS.textPrimary,
    fontFamily: FONT_FAMILY_UI,
    fontSize: "0.8125rem",
  },
  "& .MuiTableCell-head": {
    fontWeight: 700,
    color: GLASS_COLORS.textPrimary,
    backgroundColor: `var(${CSS_VAR_NAMES.surfacePanelSubtle})`,
  },
} as const;
