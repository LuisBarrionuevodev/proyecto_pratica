import { Alert, Grid } from "@mui/material";
import { useMemo } from "react";

import type { IndicadoresRiesgoResponse } from "../../../api/indicadoresApi";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import { DashboardDonutLegendCard } from "./DashboardDonutLegendCard";
import { DashboardHorizontalBarChartCard } from "./DashboardHorizontalBarChartCard";
import type { DashboardRankingBarItem } from "./DashboardRankingBarList";
import { DashboardMercaderiaDecomisadaCard } from "./DashboardMercaderiaDecomisadaCard";
import { DashboardSectionBlock } from "./DashboardSectionBlock";

type Props = {
  data: IndicadoresRiesgoResponse | null;
  mercaderiaDecomisadaKg: number | null | undefined;
  loading: boolean;
  error: string | null;
};

/**
 * Riesgo bromatológico: barras (rubros) + donuts (motivos) + total kg con distribución.
 */
export function DashboardRiesgoSection({
  data,
  mercaderiaDecomisadaKg,
  loading,
  error,
}: Props) {
  const topRubros = useMemo<DashboardRankingBarItem[]>(
    () => (data?.top_rubros ?? []).map((r) => ({ label: r.rubro, value: r.cantidad })),
    [data?.top_rubros],
  );

  const topMotivosNotif = useMemo(
    () =>
      (data?.top_motivos_notificacion ?? []).map((m) => ({
        label: m.motivo,
        value: m.cantidad,
      })),
    [data?.top_motivos_notificacion],
  );

  const topMotivosComp = useMemo(
    () =>
      (data?.top_motivos_comprobacion ?? []).map((m) => ({
        label: m.motivo,
        value: m.cantidad,
      })),
    [data?.top_motivos_comprobacion],
  );

  return (
    <DashboardSectionBlock title="Riesgo bromatológico">
      {error ? (
        <Alert severity="warning" sx={{ ...alertBaseStyles, mb: 1.25 }}>
          {error}
        </Alert>
      ) : null}

      <Grid container spacing={1.5} alignItems="stretch">
        <Grid size={{ xs: 12, md: 6 }} sx={{ display: "flex" }}>
          <DashboardHorizontalBarChartCard
            title="Top rubros intervenidos"
            items={topRubros}
            emptyMessage="Sin rubros con actividad en el período."
            maxItems={7}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }} sx={{ display: "flex" }}>
          <DashboardDonutLegendCard
            title="Motivos de notificación"
            items={topMotivosNotif}
            emptyMessage="Sin motivos de notificación en el período."
            centerCaption="Actas"
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }} sx={{ display: "flex" }}>
          <DashboardDonutLegendCard
            title="Motivos de comprobación"
            items={topMotivosComp}
            emptyMessage="Sin motivos de comprobación en el período."
            centerCaption="Actas"
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }} sx={{ display: "flex" }}>
          <DashboardMercaderiaDecomisadaCard
            kg={mercaderiaDecomisadaKg}
            rubroItems={data?.decomiso_kg_por_rubro ?? []}
          />
        </Grid>
      </Grid>
    </DashboardSectionBlock>
  );
}
