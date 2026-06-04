import { Alert, Grid } from "@mui/material";
import { useMemo } from "react";

import type { IndicadoresRiesgoResponse } from "../../../api/indicadoresApi";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import ChartCard from "./ChartCard";
import {
  DashboardCompactRankingCard,
  type DashboardRankingItem,
} from "./DashboardCompactRankingCard";
import { DashboardDecomisoKgPorRubroDonut } from "./DashboardDecomisoKgPorRubroDonut";
import { DashboardSectionBlock } from "./DashboardSectionBlock";

type Props = {
  data: IndicadoresRiesgoResponse | null;
  loading: boolean;
  error: string | null;
};

/**
 * Riesgo bromatológico: rankings y donut kg/rubro desde `/api/indicadores/riesgo`.
 */
export function DashboardRiesgoSection({ data, loading, error }: Props) {
  const topRubros = useMemo<DashboardRankingItem[]>(
    () => (data?.top_rubros ?? []).map((r) => ({ label: r.rubro, value: r.cantidad })),
    [data?.top_rubros]
  );

  const topMotivosNotif = useMemo<DashboardRankingItem[]>(
    () =>
      (data?.top_motivos_notificacion ?? []).map((m) => ({
        label: m.motivo,
        value: m.cantidad,
      })),
    [data?.top_motivos_notificacion]
  );

  const topMotivosComp = useMemo<DashboardRankingItem[]>(
    () =>
      (data?.top_motivos_comprobacion ?? []).map((m) => ({
        label: m.motivo,
        value: m.cantidad,
      })),
    [data?.top_motivos_comprobacion]
  );

  const decomisoPorRubro = data?.decomiso_kg_por_rubro ?? [];
  const sectionLoading = loading && !data;

  return (
    <DashboardSectionBlock title="Riesgo bromatológico">
      {error ? (
        <Alert severity="warning" sx={{ ...alertBaseStyles, mb: 1.25 }}>
          {error}
        </Alert>
      ) : null}

      <Grid container spacing={1.5}>
        <Grid size={{ xs: 12, md: 6 }}>
          <DashboardCompactRankingCard
            title="Top rubros"
            items={topRubros}
            loading={sectionLoading}
            emptyMessage="Sin rubros con actividad en el período."
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <ChartCard compact title="Kg decomisados por rubro" loading={sectionLoading}>
            <DashboardDecomisoKgPorRubroDonut
              items={decomisoPorRubro}
              loading={sectionLoading}
            />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <DashboardCompactRankingCard
            title="Top motivos de notificación"
            items={topMotivosNotif}
            loading={sectionLoading}
            emptyMessage="Sin motivos de notificación en el período."
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <DashboardCompactRankingCard
            title="Top motivos de comprobación"
            items={topMotivosComp}
            loading={sectionLoading}
            emptyMessage="Sin motivos de comprobación en el período."
          />
        </Grid>
      </Grid>
    </DashboardSectionBlock>
  );
}
