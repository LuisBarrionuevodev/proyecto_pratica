import { Box, Typography } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { useMemo } from "react";

import type { IndicadoresActasPorTipo } from "../../../api/indicadoresApi";
import { ChartStyle, dashboardEmptyStateCompactSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const ACTA_ITEMS: { key: keyof IndicadoresActasPorTipo; label: string; color: string }[] = [
  { key: "inspeccion", label: "Inspección", color: GLASS_COLORS.primary },
  { key: "notificacion", label: "Notificación", color: "#4A9FD4" },
  { key: "comprobacion", label: "Comprobación", color: "#22BF75" },
  { key: "clausura", label: "Clausura", color: "#F5A623" },
  { key: "decomiso", label: "Decomiso", color: "#9B7EDE" },
];

type Props = {
  actas: IndicadoresActasPorTipo;
  loading?: boolean;
};

function totalActas(actas: IndicadoresActasPorTipo): number {
  return (
    actas.inspeccion +
    actas.notificacion +
    actas.comprobacion +
    actas.clausura +
    actas.decomiso
  );
}

/**
 * Barras verticales analytics: composición de actas labradas por tipo.
 */
export function DashboardActasPorTipoChart({ actas, loading }: Props) {
  const chart = useMemo(() => {
    const labels = ACTA_ITEMS.map((i) => i.label);
    const values = ACTA_ITEMS.map((i) => actas[i.key]);
    const colors = ACTA_ITEMS.map((i) => i.color);
    const total = totalActas(actas);
    if (total === 0) return null;
    return { labels, values, colors };
  }, [actas]);

  if (loading) {
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

  return (
    <BarChart
      xAxis={[
        {
          scaleType: "band",
          data: chart.labels,
          tickLabelStyle: { fontSize: 11, angle: 0 },
        },
      ]}
      yAxis={[{ disableLine: false, tickMinStep: 1 }]}
      series={[
        {
          data: chart.values,
          label: "Actas",
          color: GLASS_COLORS.primary,
        },
      ]}
      barLabel="value"
      grid={{ horizontal: true }}
      height={220}
      margin={{ left: 40, right: 16, top: 12, bottom: 36 }}
      sx={ChartStyle}
    />
  );
}
