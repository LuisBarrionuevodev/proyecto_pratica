import { Box, Typography } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { useMemo } from "react";

import type { IndicadoresActasLabradasMes } from "../../../api/indicadoresApi";
import { ChartStyle, dashboardEmptyStateCompactSx } from "../../../styles/DashboardStyles";

const MESES_CORTO = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];

function mesLabel(anio: number, mes: number): string {
  const m = MESES_CORTO[mes - 1] ?? String(mes);
  return `${m} ${String(anio).slice(-2)}`;
}

interface Props {
  items: IndicadoresActasLabradasMes[];
  loading?: boolean;
}

/**
 * Tendencia mensual de actas labradas (sin previas/origen).
 */
const ActuacionesMensualesChart = ({ items, loading }: Props) => {
  const chart = useMemo(() => {
    if (!items.length) return null;
    const labels = items.map((i) => mesLabel(i.anio, i.mes));
    return {
      labels,
      inspeccion: items.map((i) => i.inspeccion),
      notificacion: items.map((i) => i.notificacion),
      comprobacion: items.map((i) => i.comprobacion),
      clausura: items.map((i) => i.clausura),
      decomiso: items.map((i) => i.decomiso),
    };
  }, [items]);

  if (loading && !items.length) {
    return (
      <Box sx={dashboardEmptyStateCompactSx}>
        <Typography variant="body2">Cargando…</Typography>
      </Box>
    );
  }

  if (!chart) {
    return (
      <Box sx={dashboardEmptyStateCompactSx}>
        <Typography variant="body2">Sin actas labradas en el período.</Typography>
      </Box>
    );
  }

  const height = Math.min(260, Math.max(180, chart.labels.length * 32 + 72));

  return (
    <BarChart
      xAxis={[{ scaleType: "band", data: chart.labels }]}
      series={[
        { label: "Inspección", data: chart.inspeccion, stack: "total" },
        { label: "Notificación", data: chart.notificacion, stack: "total" },
        { label: "Comprobación", data: chart.comprobacion, stack: "total" },
        { label: "Clausura", data: chart.clausura, stack: "total" },
        { label: "Decomiso", data: chart.decomiso, stack: "total" },
      ]}
      height={height}
      sx={ChartStyle}
    />
  );
};

export default ActuacionesMensualesChart;
