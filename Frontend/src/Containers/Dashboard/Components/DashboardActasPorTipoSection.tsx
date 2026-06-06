import { Alert } from "@mui/material";

import type { IndicadoresActasPorTipo } from "../../../api/indicadoresApi";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import { DashboardActasPorTipoChart } from "./DashboardActasPorTipoChart";
import { DashboardAnalyticsChartCard } from "./DashboardAnalyticsChartCard";
import { DashboardSectionBlock } from "./DashboardSectionBlock";

const ACTAS_VACIAS: IndicadoresActasPorTipo = {
  inspeccion: 0,
  notificacion: 0,
  comprobacion: 0,
  clausura: 0,
  decomiso: 0,
};

type Props = {
  actas: IndicadoresActasPorTipo | undefined;
  loading: boolean;
  error: string | null;
};

/**
 * Composición de actas labradas por tipo (chart analytics).
 */
export function DashboardActasPorTipoSection({ actas, loading, error }: Props) {
  const data = actas ?? ACTAS_VACIAS;
  const sectionLoading = loading && actas == null;

  return (
    <DashboardSectionBlock title="Actas labradas por tipo">
      {error ? (
        <Alert severity="warning" sx={{ ...alertBaseStyles, mb: 1.25 }}>
          {error}
        </Alert>
      ) : null}
      <DashboardAnalyticsChartCard title="Distribución por tipo" loading={sectionLoading}>
        <DashboardActasPorTipoChart actas={data} loading={sectionLoading} />
      </DashboardAnalyticsChartCard>
    </DashboardSectionBlock>
  );
}
