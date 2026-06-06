import { Alert, Box } from "@mui/material";

import type { IndicadoresPendientesResponse } from "../../../api/indicadoresApi";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import { DashboardAnalyticsChartCard } from "./DashboardAnalyticsChartCard";
import { DashboardAnalyticsKpiCard } from "./DashboardAnalyticsKpiCard";
import { DashboardDistritosPendientesTable } from "./DashboardDistritosPendientesTable";
import { DashboardMetricGrid } from "./DashboardMetricGrid";
import { DashboardSectionBlock } from "./DashboardSectionBlock";

type Props = {
  data: IndicadoresPendientesResponse | null;
  loading: boolean;
  error: string | null;
};

/**
 * Operativo / pendientes: cola por tipo de iniciador y ranking por distrito.
 */
export function DashboardPendientesSection({ data, loading, error }: Props) {
  const kpis = data?.kpis;
  const showValues = !loading && !error && data != null;
  const sectionLoading = loading && !data;

  const kpiValue = (value: number | undefined): number | string => {
    if (sectionLoading) return "…";
    if (!showValues || value == null) return "—";
    return value;
  };

  return (
    <DashboardSectionBlock title="Operativo / pendientes">
      {error ? (
        <Alert severity="warning" sx={{ ...alertBaseStyles, mb: 1.25 }}>
          {error}
        </Alert>
      ) : null}

      <DashboardMetricGrid
        columns={{ xs: "1fr 1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)", lg: "repeat(5, 1fr)" }}
      >
        <DashboardAnalyticsKpiCard
          label="Relevamientos pendientes"
          value={kpiValue(kpis?.relevamientos_pendientes)}
          loading={sectionLoading}
          accent="primary"
        />
        <DashboardAnalyticsKpiCard
          label="Reins. oficio pendientes"
          value={kpiValue(kpis?.reinspecciones_oficio_pendientes)}
          loading={sectionLoading}
          accent="teal"
        />
        <DashboardAnalyticsKpiCard
          label="Reins. notificación pendientes"
          value={kpiValue(kpis?.reinspecciones_notificacion_pendientes)}
          loading={sectionLoading}
          accent="primary"
        />
        <DashboardAnalyticsKpiCard
          label="Denuncias pendientes"
          value={kpiValue(kpis?.denuncias_pendientes)}
          loading={sectionLoading}
          accent="amber"
        />
        <DashboardAnalyticsKpiCard
          label="Sin geolocalización"
          value={kpiValue(kpis?.pendientes_geolocalizacion)}
          loading={sectionLoading}
          accent="neutral"
        />
      </DashboardMetricGrid>

      <Box sx={{ mt: 1.25 }}>
        <DashboardAnalyticsChartCard
          title="Distritos con más pendientes"
          loading={sectionLoading}
        >
          <DashboardDistritosPendientesTable
          rows={data?.distritos_con_mas_pendientes ?? []}
          loading={sectionLoading}
          />
        </DashboardAnalyticsChartCard>
      </Box>
    </DashboardSectionBlock>
  );
}
