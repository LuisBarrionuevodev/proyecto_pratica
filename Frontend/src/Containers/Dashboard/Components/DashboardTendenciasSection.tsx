import { Alert, Grid } from "@mui/material";

import type { IndicadoresResumenResponse } from "../../../api/indicadoresApi";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import ActuacionesMensualesChart from "./DashboardActuacionMensual";
import ChartCard from "./ChartCard";
import DecomisoMensualChart from "./DashboardDecomiso";
import { DashboardSectionBlock } from "./DashboardSectionBlock";

type Props = {
  data: IndicadoresResumenResponse | null;
  loading: boolean;
  error: string | null;
};

/**
 * Tendencias mensuales desde `/api/indicadores/resumen` (actas labradas y kg decomisados).
 */
export function DashboardTendenciasSection({ data, loading, error }: Props) {
  const sectionLoading = loading && !data;

  return (
    <DashboardSectionBlock title="Tendencias">
      {error ? (
        <Alert severity="warning" sx={{ ...alertBaseStyles, mb: 1.25 }}>
          {error}
        </Alert>
      ) : null}

      <Grid container spacing={1.5}>
        <Grid size={{ xs: 12, lg: 8 }}>
          <ChartCard compact title="Actas labradas — tendencia mensual" loading={sectionLoading}>
            <ActuacionesMensualesChart
              items={data?.actas_labradas_mensual ?? []}
              loading={sectionLoading}
            />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <ChartCard compact title="Kg decomisados" loading={sectionLoading}>
            <DecomisoMensualChart
              decomisoKg={data?.decomiso_kg ?? null}
              loading={sectionLoading}
            />
          </ChartCard>
        </Grid>
      </Grid>
    </DashboardSectionBlock>
  );
}
