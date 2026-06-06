import { Box, Card, LinearProgress, Typography } from "@mui/material";

import {
  DASHBOARD_KPI_CARD_MIN_HEIGHT,
  dashboardAnalyticsCardSx,
  dashboardAnalyticsKpiLabelSx,
  dashboardAnalyticsKpiValueSx,
} from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

export type DashboardKpiAccent = "primary" | "teal" | "amber" | "neutral";

const ACCENT_COLORS: Record<DashboardKpiAccent, string> = {
  primary: GLASS_COLORS.primary,
  teal: "#22BF75",
  amber: "#F5A623",
  neutral: "rgba(255,255,255,0.35)",
};

type Props = {
  label: string;
  value: number | string;
  unit?: string;
  loading?: boolean;
  accent?: DashboardKpiAccent;
  showPeriodSubtitle?: boolean;
};

/** Barras decorativas neutras (no representan serie temporal). */
function KpiNeutralMicroBars({ color }: { color: string }) {
  const heights = [0.32, 0.52, 0.38, 0.68, 0.44];
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "flex-end",
        gap: "3px",
        height: 40,
        opacity: 0.5,
        flexShrink: 0,
      }}
      aria-hidden
    >
      {heights.map((h, i) => (
        <Box
          key={i}
          sx={{
            width: 4,
            height: `${h * 100}%`,
            bgcolor: color,
            borderRadius: "2px",
          }}
        />
      ))}
    </Box>
  );
}

/**
 * KPI estilo MUI Dashboard Template (dark/glass Digitaliza).
 */
export function DashboardAnalyticsKpiCard({
  label,
  value,
  unit,
  loading = false,
  accent = "primary",
  showPeriodSubtitle = false,
}: Props) {
  const accentColor = ACCENT_COLORS[accent];

  return (
    <Card
      sx={{
        ...dashboardAnalyticsCardSx,
        p: { xs: 1.5, sm: 1.75 },
        position: "relative",
        overflow: "hidden",
        minWidth: 0,
        minHeight: DASHBOARD_KPI_CARD_MIN_HEIGHT,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      {loading ? (
        <LinearProgress
          sx={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, borderRadius: 0 }}
        />
      ) : null}

      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 1,
        }}
      >
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography sx={dashboardAnalyticsKpiLabelSx}>{label}</Typography>
          <Box sx={{ display: "flex", alignItems: "baseline", gap: 0.5, flexWrap: "wrap" }}>
            <Typography sx={dashboardAnalyticsKpiValueSx}>{loading ? "…" : value}</Typography>
            {unit && !loading ? (
              <Typography
                variant="caption"
                sx={{
                  fontFamily: '"Tactic Sans", sans-serif',
                  color: GLASS_COLORS.textMuted,
                  fontWeight: 600,
                  fontSize: "0.7rem",
                }}
              >
                {unit}
              </Typography>
            ) : null}
          </Box>
          {showPeriodSubtitle ? (
            <Typography
              variant="caption"
              sx={{
                display: "block",
                mt: 0.5,
                fontFamily: '"Tactic Sans", sans-serif',
                color: GLASS_COLORS.textMuted,
                fontSize: "0.65rem",
              }}
            >
              Período seleccionado
            </Typography>
          ) : null}
        </Box>
        <KpiNeutralMicroBars color={accentColor} />
      </Box>

      <Box
        sx={{
          mt: 1.25,
          height: 3,
          borderRadius: 1,
          bgcolor: "rgba(255,255,255,0.06)",
          overflow: "hidden",
        }}
        aria-hidden
      >
        <Box
          sx={{
            width: "38%",
            height: "100%",
            bgcolor: accentColor,
            opacity: 0.35,
            borderRadius: 1,
          }}
        />
      </Box>
    </Card>
  );
}
