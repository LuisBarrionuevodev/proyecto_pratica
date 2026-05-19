import { Box, Typography } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";

import type { IndicadoresActuacionPorTipoOperativo } from "../../../api/indicadoresApi";
import { humanizarTipoActuacion } from "../../ActasComprobacion/utils/documentalLabelFormat";
import { ChartStyle, dashboardEmptyStateSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

interface Props {
  items: IndicadoresActuacionPorTipoOperativo[];
}

const ActuacionesPorTipoChart = ({ items }: Props) => {
  if (!items.length) {
    return (
      <Box sx={dashboardEmptyStateSx}>
        <Typography variant="body2">Sin actuaciones en el periodo.</Typography>
      </Box>
    );
  }

  const ordered = [...items].reverse();
  const labels = ordered.map((i) => humanizarTipoActuacion(i.tipo));
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
      margin={{ left: 120, right: 12, top: 8, bottom: 24 }}
      sx={ChartStyle}
    />
  );
};

export default ActuacionesPorTipoChart;
