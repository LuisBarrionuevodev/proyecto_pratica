import { Alert, Box } from "@mui/material";

import type { IndicadoresActasPorTipo, IndicadoresEjecutivoResponse } from "../../../api/indicadoresApi";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import { DashboardActasPorTipoMini } from "./DashboardActasPorTipoChips";
import { DashboardExecutiveKpiGrid } from "./DashboardExecutiveKpiGrid";
import KPI from "./DashboardKPI";
import { dashboardEmptyStateCompactSx } from "../../../styles/DashboardStyles";
import { DashboardSectionBlock } from "./DashboardSectionBlock";

const ACTAS_VACIAS: IndicadoresActasPorTipo = {
  inspeccion: 0,
  notificacion: 0,
  comprobacion: 0,
  clausura: 0,
  decomiso: 0,
};

type Props = {
  data: IndicadoresEjecutivoResponse | null;
  loading: boolean;
  error: string | null;
};

function formatKg(kg: number): string {
  if (Number.isInteger(kg)) {
    return String(kg);
  }
  return kg.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

/**
 * Resumen ejecutivo: KPIs desde `/api/indicadores/ejecutivo` y actas por tipo.
 */
export function DashboardEjecutivoSection({ data, loading, error }: Props) {
  const kpis = data?.kpis;
  const actas = data?.actas_por_tipo ?? ACTAS_VACIAS;
  const showValues = !loading && !error && data != null;

  const kpiValue = (value: number | undefined): number | string => {
    if (loading) return "…";
    if (!showValues || value == null) return "—";
    return value;
  };

  return (
    <DashboardSectionBlock first title="Resumen ejecutivo">
      {error ? (
        <Alert severity="warning" sx={{ ...alertBaseStyles, mb: 1.25 }}>
          {error}
        </Alert>
      ) : null}

      <DashboardExecutiveKpiGrid
        columns={{ xs: "1fr 1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)", lg: "repeat(4, 1fr)" }}
      >
        <KPI compact title="Actuaciones realizadas" value={kpiValue(kpis?.actuaciones_realizadas)} />
        <KPI compact title="Actas labradas" value={kpiValue(kpis?.actas_labradas)} />
        <KPI
          compact
          title="Reins. notificación realizadas"
          value={kpiValue(kpis?.reinspecciones_notificacion_realizadas)}
        />
        <KPI
          compact
          title="Ratif. clausura realizadas"
          value={kpiValue(kpis?.ratificaciones_clausura_realizadas)}
        />
        <KPI
          compact
          title="Ratif. decomiso realizadas"
          value={kpiValue(kpis?.ratificaciones_decomiso_realizadas)}
        />
        <KPI
          compact
          title="Verificar e informar realizadas"
          value={kpiValue(kpis?.verificar_informar_realizadas)}
        />
        <KPI
          compact
          title="Kg decomisados"
          value={
            loading
              ? "…"
              : showValues && kpis != null
                ? formatKg(kpis.mercaderia_decomisada_kg)
                : "—"
          }
        />
      </DashboardExecutiveKpiGrid>

      <Box sx={{ mt: 1.25 }}>
        {error && !data ? (
          <Box sx={dashboardEmptyStateCompactSx}>Actas por tipo no disponibles.</Box>
        ) : (
          <DashboardActasPorTipoMini actas={actas} loading={loading} />
        )}
      </Box>
    </DashboardSectionBlock>
  );
}
