import { Box, Typography } from "@mui/material";
import { LineChart } from "@mui/x-charts/LineChart";
import { ChartStyle } from "../../../styles/DashboardStyles";
import type { IndicadoresDecomisoKg } from "../../../api/indicadoresApi";

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
      <Box sx={{ height: 300, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Typography variant="body2" color="rgba(255,255,255,0.6)">
          {loading ? "Cargando…" : "Sin datos."}
        </Typography>
      </Box>
    );
  }

  if (decomisoKg.por_mes.length === 0) {
    return (
      <Box sx={{ minHeight: 200, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 1 }}>
        <Typography variant="body2" color="rgba(255,255,255,0.6)">
          Sin decomisos en el periodo seleccionado.
        </Typography>
        <Typography variant="caption" color="rgba(255,255,255,0.45)">
          Total: {formatKg(decomisoKg.total_kg)} kg
        </Typography>
      </Box>
    );
  }

  const labels = decomisoKg.por_mes.map((p) => etiquetaMes(p.anio, p.mes));
  const values = decomisoKg.por_mes.map((p) => p.kg);

  return (
    <Box>
      <Typography variant="caption" color="rgba(255,255,255,0.65)" display="block" sx={{ mb: 1 }}>
        Total periodo: <strong style={{ color: "#fff" }}>{formatKg(decomisoKg.total_kg)} kg</strong>
      </Typography>
      <LineChart
        xAxis={[{ scaleType: "point", data: labels }]}
        series={[
          {
            color: "#0166FF",
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
