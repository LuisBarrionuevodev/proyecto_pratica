import { Alert, Box, Grid } from "@mui/material";
import { memo, useMemo } from "react";

import type { IndicadoresNoRealizadasResponse } from "../../../api/indicadoresApi";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import { DashboardAnalyticsChartCard } from "./DashboardAnalyticsChartCard";
import { DashboardContraproducenciasTable } from "./DashboardContraproducenciasTable";
import { DashboardHorizontalBarChartCard } from "./DashboardHorizontalBarChartCard";
import type { DashboardRankingBarItem } from "./DashboardRankingBarList";
import { DashboardSectionBlock } from "./DashboardSectionBlock";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { buildContraproducenciasResumen } from "../utils/noRealizadasContraproducencias";

type Props = {
  data: IndicadoresNoRealizadasResponse | null;
  loading: boolean;
  error: string | null;
};

function formatDistritoNombre(nombre: string): string {
  const t = nombre.trim();
  if (t.toLowerCase() === "sin distrito" || t === "SIN_DISTRITO") {
    return "Sin distrito";
  }
  return t;
}

/**
 * No realizadas: indicador general por contraproducencia (no por tipo operativo).
 */
export const DashboardNoRealizadasSection = memo(function DashboardNoRealizadasSection({
  data,
  error,
}: Props) {
  const resumen = useMemo(() => buildContraproducenciasResumen(data), [data]);
  const totalNoRealizadas = resumen.total;

  const distritosRanking = useMemo<DashboardRankingBarItem[]>(
    () =>
      (data?.distritos_con_mas_no_realizadas ?? []).map((d) => ({
        label: formatDistritoNombre(d.distrito_nombre),
        value: d.cantidad,
      })),
    [data?.distritos_con_mas_no_realizadas],
  );

  const contraproducenciasEmptyMessage =
    totalNoRealizadas === 0 && data != null && !error
      ? "Sin no realizadas en el período seleccionado."
      : "Sin motivos registrados en el período.";

  return (
    <DashboardSectionBlock title="No realizadas">
      {error ? (
        <Alert severity="warning" sx={{ ...alertBaseStyles, mb: 1.25 }}>
          {error}
        </Alert>
      ) : null}

      <Grid container spacing={1.5} alignItems="stretch">
        <Grid size={{ xs: 12, lg: 7 }} sx={{ display: "flex" }}>
          <DashboardAnalyticsChartCard title="Principales contraproducencias" fillHeight>
            <DashboardContraproducenciasTable
              rows={resumen.rows}
              emptyMessage={contraproducenciasEmptyMessage}
              showZeroRows
            />
          </DashboardAnalyticsChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }} sx={{ display: "flex" }}>
          <DashboardHorizontalBarChartCard
            title="Distritos con más no realizadas"
            items={distritosRanking}
            emptyMessage="Sin no realizadas por distrito en el período."
            color={GLASS_COLORS.primary}
          />
        </Grid>
      </Grid>
    </DashboardSectionBlock>
  );
});
