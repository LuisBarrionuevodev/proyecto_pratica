import { Box, Typography } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";

import type { IndicadoresReinspeccionesRealizadas } from "../../../api/indicadoresApi";
import { ChartStyle, dashboardEmptyStateSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

interface Props {
  data: IndicadoresReinspeccionesRealizadas | null;
}

/**
 * Reinspecciones efectivamente realizadas (visita cerrada con actuación vinculada).
 */
const ReinspeccionesRealizadasChart = ({ data }: Props) => {
  const notif = data?.notificacion ?? 0;
  const oficio = data?.oficio ?? 0;
  const total = notif + oficio;

  if (total === 0) {
    return (
      <Box sx={dashboardEmptyStateSx}>
        <Typography variant="body2">
          Sin reinspecciones realizadas en el periodo (fecha de cierre de ruta).
        </Typography>
      </Box>
    );
  }

  return (
    <BarChart
      xAxis={[{ scaleType: "band", data: ["Por notificación", "Por oficio"] }]}
      series={[
        {
          color: GLASS_COLORS.primary,
          data: [notif, oficio],
          label: "Reinspecciones",
        },
      ]}
      height={260}
      sx={ChartStyle}
    />
  );
};

export default ReinspeccionesRealizadasChart;
