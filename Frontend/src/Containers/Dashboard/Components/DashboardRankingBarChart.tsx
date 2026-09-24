import { Box, Tooltip, Typography } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { useMemo } from "react";

import { ChartStyle, dashboardEmptyStateCompactSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

export type DashboardRankingChartItem = {
  label: string;
  value: number;
};

const MAX_LABEL = 28;
const ROW_PX = 30;
const MIN_HEIGHT = 120;
const MAX_HEIGHT = 280;

function truncateLabel(label: string): string {
  const t = label.trim();
  if (t.length <= MAX_LABEL) return t;
  return `${t.slice(0, MAX_LABEL - 1)}…`;
}

function normalizeLabel(label: string): string {
  return label
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .trim();
}

type Props = {
  items: DashboardRankingChartItem[];
  loading?: boolean;
  emptyMessage?: string;
  maxItems?: number;
  color?: string;
};

/**
 * Gráfico de barras horizontales para rankings (MUI X Charts).
 */
export function DashboardRankingBarChart({
  items,
  loading = false,
  emptyMessage = "Sin datos en el período.",
  maxItems = 8,
  color = GLASS_COLORS.primary,
}: Props) {
  const slice = useMemo(
    () =>
      items
        .slice(0, maxItems)
        .map((i) => ({ label: normalizeLabel(i.label), value: i.value })),
    [items, maxItems],
  );

  const chartHeight = useMemo(() => {
    if (slice.length === 0) return MIN_HEIGHT;
    return Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, slice.length * ROW_PX + 36));
  }, [slice.length]);

  if (loading && slice.length === 0) {
    return (
      <Box sx={dashboardEmptyStateCompactSx}>
        <Typography variant="body2">Cargando…</Typography>
      </Box>
    );
  }

  if (slice.length === 0) {
    return (
      <Box sx={dashboardEmptyStateCompactSx}>
        <Typography variant="body2">{emptyMessage}</Typography>
      </Box>
    );
  }

  const displayLabels = slice.map((i) => truncateLabel(i.label));
  const values = slice.map((i) => i.value);

  return (
    <Box>
      <BarChart
        layout="horizontal"
        yAxis={[
          {
            scaleType: "band",
            data: displayLabels,
            tickLabelStyle: { fontSize: 11 },
          },
        ]}
        xAxis={[
          {
            disableLine: true,
            disableTicks: true,
          },
        ]}
        series={[
          {
            data: values,
            color,
            valueFormatter: (v) => (v == null ? "" : String(v)),
          },
        ]}
        barLabel="value"
        grid={{ vertical: true }}
        height={chartHeight}
        margin={{ left: 4, right: 28, top: 4, bottom: 4 }}
        sx={ChartStyle}
      />
      {slice.some((i) => i.label.length > MAX_LABEL) ? (
        <Box sx={{ mt: 0.5, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
          {slice
            .filter((i) => i.label.length > MAX_LABEL)
            .map((i) => (
              <Tooltip key={i.label} title={i.label}>
                <Typography
                  variant="caption"
                  sx={{ color: GLASS_COLORS.textMuted, fontSize: "0.6rem", cursor: "default" }}
                >
                  {truncateLabel(i.label)}
                </Typography>
              </Tooltip>
            ))}
        </Box>
      ) : null}
    </Box>
  );
}
