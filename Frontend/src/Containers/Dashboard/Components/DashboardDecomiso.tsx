import { Box, Typography } from "@mui/material";
import { LineChart } from "@mui/x-charts/LineChart";

import type { IndicadoresDecomisoKg } from "../../../api/indicadoresApi";
import { ChartStyle, dashboardEmptyStateSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const MESES_CORTO = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

function etiquetaMes(anio: number, mes: number): string {
  const m = MESES_CORTO[mes - 1] ?? String(mes);
  return `${m} ${anio}`;
}

function formatKg(n: number): string {
  if (n === 0) return "0";
  const s = n.toFixed(3).replace(/\.?0+$/, "");
  return s;
}

interface Props {
  /** null si aún no hay payload del resumen. */
  decomisoKg: IndicadoresDecomisoKg | null;
  loading?: boolean;
}

/**
 * Línea de kg decomisados por mes (fecha de actuación) y total en el conjunto filtrado.
 */
const DecomisoMensualChart = ({ decomisoKg, loading }: Props) => {
  if (loading || decomisoKg === null) {
    return (
      <Box sx={dashboardEmptyStateSx}>
        <Typography variant="body2">{loading ? "Cargando…" : "Sin datos."}</Typography>
      </Box>
    );
  }

  if (decomisoKg.por_mes.length === 0) {
    return (
      <Box sx={{ ...dashboardEmptyStateSx, flexDirection: "column", gap: 1 }}>
        <Typography variant="body2">Sin decomisos en el periodo seleccionado.</Typography>
        <Typography variant="caption" sx={{ color: GLASS_COLORS.textSecondary }}>
          Total: {formatKg(decomisoKg.total_kg)} kg
        </Typography>
      </Box>
    );
  }

  const labels = decomisoKg.por_mes.map((p) => etiquetaMes(p.anio, p.mes));
  const values = decomisoKg.por_mes.map((p) => p.kg);

  return (
    <Box>
      <Typography variant="caption" sx={{ color: GLASS_COLORS.textSecondary, display: "block", mb: 1, fontFamily: '"Tactic Sans", sans-serif' }}>
        Total periodo: <strong style={{ color: GLASS_COLORS.textPrimary }}>{formatKg(decomisoKg.total_kg)} kg</strong>
      </Typography>
      <LineChart
        xAxis={[{ scaleType: "point", data: labels }]}
        series={[
          {
            color: GLASS_COLORS.primary,
            label: "Kg decomisados",
            data: values,
          },
        ]}
        height={300}
        sx={ChartStyle}
      />
    </Box>
  );
};

export default DecomisoMensualChart;
