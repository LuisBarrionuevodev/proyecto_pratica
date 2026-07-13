import { Box, Typography } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { useMemo } from "react";

import type { IndicadoresActasPorTipo } from "../../../api/indicadoresApi";
import { ChartStyle, dashboardEmptyStateCompactSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

const ACTA_ITEMS: { key: keyof IndicadoresActasPorTipo; label: string }[] = [
  { key: "inspeccion", label: "Inspección" },
  { key: "notificacion", label: "Notificación" },
  { key: "comprobacion", label: "Comprobación" },
  { key: "clausura", label: "Clausura" },
  { key: "decomiso", label: "Decomiso" },
];

type Props = {
  actas: IndicadoresActasPorTipo;
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
export function DashboardActasPorTipoChart({ actas }: Props) {
  const chart = useMemo(() => {
    const labels = ACTA_ITEMS.map((i) => i.label);
    const values = ACTA_ITEMS.map((i) => actas[i.key]);
    const total = totalActas(actas);
    if (total === 0) return null;
    return { labels, values };
  }, [actas]);

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
          tickLabelStyle: { fontSize: 11 },
        },
      ]}
      yAxis={[
        {
          tickMinStep: 1,
          disableLine: false,
        },
      ]}
      series={[
        {
          data: chart.values,
          label: "Actas",
          color: GLASS_COLORS.primary,
        },
      ]}
      barLabel="value"
      grid={{ horizontal: true }}
      height={240}
      margin={{ left: 36, right: 12, top: 16, bottom: 40 }}
      sx={ChartStyle}
    />
  );
}
