import { Box, Typography } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { ChartStyle } from "../../../styles/DashboardStyles";
import type { IndicadoresRubroTopItem } from "../../../api/indicadoresApi";

const MAX_LABEL = 42;

function truncateLabel(nombre: string): string {
  const t = nombre.trim();
  if (t.length <= MAX_LABEL) return t;
  return `${t.slice(0, MAX_LABEL - 1)}…`;
}

interface Props {
  items: IndicadoresRubroTopItem[];
}

/**
 * Ranking horizontal de rubros por cantidad de actuaciones (mismo filtro que el resumen).
 * Actuaciones sin domicilio o sin rubro no entran en este ranking.
 */
const TopRubrosChart = ({ items }: Props) => {
  if (!items.length) {
    return (
      <Box sx={{ minHeight: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Typography variant="body2" color="rgba(255,255,255,0.6)" textAlign="center" px={2}>
          Sin actuaciones con rubro asignado en el periodo (o el domicilio no tiene rubro).
        </Typography>
      </Box>
    );
  }

  // Eje Y: primer índice suele quedar abajo; invertimos para que el #1 quede arriba.
  const ordered = [...items].reverse();
  const labels = ordered.map((r) => truncateLabel(r.nombre));
  const counts = ordered.map((r) => r.count);
  const barHeight = Math.max(280, labels.length * 36);

  return (
    <BarChart
      layout="horizontal"
      yAxis={[{ scaleType: "band", data: labels }]}
      series={[
        {
          color: "#0166FF",
          data: counts,
          label: "Actuaciones",
        },
      ]}
      height={barHeight}
      margin={{ left: 100, right: 16 }}
      sx={ChartStyle}
    />
  );
};

export default TopRubrosChart;
