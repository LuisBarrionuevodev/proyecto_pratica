import { Box } from "@mui/material";
import { PieChart } from "@mui/x-charts/PieChart";

import type { IndicadoresDecomisoKgRubroItem } from "../../../api/indicadoresApi";
import { ChartStyle, dashboardEmptyStateCompactSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const CHART_COLORS = [
  GLASS_COLORS.primary,
  "#22BF75",
  "#4A9FD4",
  "#F5A623",
  "#9B7EDE",
  "#5C6BC0",
  "#26A69A",
  "#8D6E63",
];

type Props = {
  items: IndicadoresDecomisoKgRubroItem[];
  loading?: boolean;
};

function formatKg(kg: number): string {
  if (Number.isInteger(kg)) {
    return `${kg} kg`;
  }
  return `${kg.toLocaleString("es-AR", { maximumFractionDigits: 2 })} kg`;
}

/**
 * Donut compacto: kg decomisados por rubro (tooltip rubro + kg).
 */
export function DashboardDecomisoKgPorRubroDonut({ items, loading }: Props) {
  if (loading) {
    return <Box sx={dashboardEmptyStateCompactSx}>Cargando…</Box>;
  }

  const nonZero = items.filter((i) => i.kg > 0);
  if (!nonZero.length) {
    return (
      <Box sx={dashboardEmptyStateCompactSx}>
        Sin kilos decomisados por rubro en el período.
      </Box>
    );
  }

  const pieData = nonZero.map((row, i) => ({
    id: i,
    value: row.kg,
    label: row.rubro,
    color: CHART_COLORS[i % CHART_COLORS.length],
  }));

  const singleSlice = nonZero.length === 1;

  return (
    <PieChart
      series={[
        {
          data: pieData,
          innerRadius: 42,
          outerRadius: 72,
          paddingAngle: singleSlice ? 0 : 1,
          cornerRadius: singleSlice ? 0 : 3,
          valueFormatter: (value) => formatKg(value ?? 0),
        },
      ]}
      height={200}
      margin={{ top: 8, bottom: 8, left: 8, right: singleSlice ? 24 : 8 }}
      slotProps={{
        legend: {
          direction: singleSlice ? "row" : "column",
          position: singleSlice
            ? { vertical: "bottom", horizontal: "middle" }
            : { vertical: "middle", horizontal: "end" },
          labelStyle: {
            fontFamily: '"Tactic Sans", sans-serif',
            fontSize: 11,
            fill: GLASS_COLORS.textSecondary,
          },
        },
        tooltip: {
          sx: {
            fontFamily: '"Tactic Sans", sans-serif',
            fontSize: "0.8125rem",
          },
        },
      }}
      sx={ChartStyle}
    />
  );
}
