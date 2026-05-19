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
  height: "100%",
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
