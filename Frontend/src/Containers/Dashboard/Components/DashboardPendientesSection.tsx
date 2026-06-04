import { Alert, Box, Typography } from "@mui/material";

import type { IndicadoresPendientesResponse } from "../../../api/indicadoresApi";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import { DashboardDistritosPendientesTable } from "./DashboardDistritosPendientesTable";
import { DashboardExecutiveKpiGrid } from "./DashboardExecutiveKpiGrid";
import KPI from "./DashboardKPI";
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

  const kpiValue = (value: number | undefined): number | string => {
    if (loading) return "…";
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

      <DashboardExecutiveKpiGrid
        columns={{ xs: "1fr 1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)", lg: "repeat(5, 1fr)" }}
      >
        <KPI compact title="Relevamientos pendientes" value={kpiValue(kpis?.relevamientos_pendientes)} />
        <KPI
          compact
          title="Reins. oficio pendientes"
          value={kpiValue(kpis?.reinspecciones_oficio_pendientes)}
        />
        <KPI
          compact
          title="Reins. notificación pendientes"
          value={kpiValue(kpis?.reinspecciones_notificacion_pendientes)}
        />
        <KPI compact title="Denuncias pendientes" value={kpiValue(kpis?.denuncias_pendientes)} />
        <KPI
          compact
          title="Sin geolocalización"
          value={kpiValue(kpis?.pendientes_geolocalizacion)}
        />
      </DashboardExecutiveKpiGrid>

      <Box sx={{ mt: 1.25 }}>
        <Typography
          variant="caption"
          sx={{
            display: "block",
            mb: 0.75,
            fontFamily: '"Tactic Sans", sans-serif',
            fontWeight: 600,
            color: GLASS_COLORS.textMuted,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            fontSize: "0.65rem",
          }}
        >
          Distritos con más pendientes
        </Typography>
        <DashboardDistritosPendientesTable
          rows={data?.distritos_con_mas_pendientes ?? []}
          loading={loading && !data}
        />
      </Box>
    </DashboardSectionBlock>
  );
}
