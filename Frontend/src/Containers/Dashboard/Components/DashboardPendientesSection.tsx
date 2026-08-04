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
export function DashboardPendientesSection({ data, error }: Props) {
  const kpis = data?.kpis;

  const kpiValue = (value: number | undefined): number | string => {
    if (error || data == null) return "—";
    if (value == null) return "—";
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
        columns={{ xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)", lg: "repeat(5, 1fr)" }}
        gap={1.5}
      >
        <DashboardAnalyticsKpiCard
          label="Relevamientos pendientes"
          value={kpiValue(kpis?.relevamientos_pendientes)}
          accent="neutral"
        />
        <DashboardAnalyticsKpiCard
          label="Reins. oficio pendientes"
          value={kpiValue(kpis?.reinspecciones_oficio_pendientes)}
          accent="teal"
        />
        <DashboardAnalyticsKpiCard
          label="Reins. notificación pendientes"
          value={kpiValue(kpis?.reinspecciones_notificacion_pendientes)}
          accent="primary"
        />
        <DashboardAnalyticsKpiCard
          label="Denuncias pendientes"
          value={kpiValue(kpis?.denuncias_pendientes)}
          accent="amber"
        />
        <DashboardAnalyticsKpiCard
          label="Pendientes geolocalización"
          value={kpiValue(kpis?.pendientes_geolocalizacion)}
          accent="primary"
        />
      </DashboardMetricGrid>

      <Box sx={{ mt: 2 }}>
        <DashboardAnalyticsChartCard title="Distritos con más pendientes">
          <DashboardDistritosPendientesTable rows={data?.distritos_con_mas_pendientes ?? []} />
        </DashboardAnalyticsChartCard>
      </Box>
    </DashboardSectionBlock>
  );
}
