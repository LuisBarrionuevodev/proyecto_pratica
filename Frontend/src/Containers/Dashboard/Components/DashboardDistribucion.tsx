import { Box, Typography } from "@mui/material";
import { PieChart } from "@mui/x-charts/PieChart";

import type { IndicadoresActasPorTipo } from "../../../api/indicadoresApi";
import { ChartStyle, dashboardEmptyStateSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const COLORS = [
  GLASS_COLORS.primary,
  "#22BF75",
  "#F5A623",
  "#FA4F58",
  "#9B59B6",
];

function actasToPieData(actas: IndicadoresActasPorTipo) {
  const pairs: { label: string; value: number }[] = [
    { label: "Inspección", value: actas.inspeccion },
    { label: "Notificación", value: actas.notificacion },
    { label: "Comprobación", value: actas.comprobacion },
    { label: "Clausura", value: actas.clausura },
    { label: "Decomiso", value: actas.decomiso },
  ];
  const nonZero = pairs.filter((p) => p.value > 0);
  return nonZero.map((p, i) => ({
    id: i + 1,
    value: p.value,
    label: p.label,
    color: COLORS[i % COLORS.length],
  }));
}

interface Props {
  actas: IndicadoresActasPorTipo;
}

/**
 * Distribución de actas por tipo según agregados del backend.
 */
const DistribucionTipoChart = ({ actas }: Props) => {
  const data = actasToPieData(actas);
  if (!data.length) {
    return (
      <Box sx={dashboardEmptyStateSx}>
        <Typography variant="body2">Sin actas en el periodo seleccionado.</Typography>
      </Box>
    );
  }

  return (
    <PieChart
      series={[
        {
          data,
          innerRadius: 0,
          outerRadius: 120,
          paddingAngle: 1,
          cornerRadius: 4,
        },
      ]}
      height={300}
      sx={ChartStyle}
    />
  );
};

export default DistribucionTipoChart;