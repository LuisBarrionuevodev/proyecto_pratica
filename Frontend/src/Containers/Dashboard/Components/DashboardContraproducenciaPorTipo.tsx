import { Box, Typography } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";

import type { IndicadoresContraproducenciaPorTipo } from "../../../api/indicadoresApi";
import { ChartStyle, dashboardEmptyStateSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const MAX_LABEL = 28;

function truncate(val: string): string {
  const t = val.trim();
  if (t.length <= MAX_LABEL) return t;
  return `${t.slice(0, MAX_LABEL - 1)}…`;
}

interface Props {
  items: IndicadoresContraproducenciaPorTipo[];
}

const ContraproducenciaPorTipoChart = ({ items }: Props) => {
  if (!items.length) {
    return (
      <Box sx={dashboardEmptyStateSx}>
        <Typography variant="body2">Sin actuaciones en el periodo.</Typography>
      </Box>
    );
  }

  const ordered = [...items].reverse();
  const labels = ordered.map((i) => truncate(i.valor));
  const counts = ordered.map((i) => i.count);
  const height = Math.min(280, Math.max(140, labels.length * 28 + 48));

  return (
    <BarChart
      layout="horizontal"
      yAxis={[{ scaleType: "band", data: labels }]}
      series={[
        {
          color: GLASS_COLORS.primary,
          data: counts,
          label: "Actuaciones",
        },
      ]}
      height={height}
      margin={{ left: 88, right: 12, top: 8, bottom: 24 }}
      sx={ChartStyle}
    />
  );
};

export default ContraproducenciaPorTipoChart;
