import { Alert, Grid } from "@mui/material";
import { useMemo } from "react";

import type { IndicadoresNoRealizadasResponse } from "../../../api/indicadoresApi";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import {
  DashboardCompactRankingCard,
  type DashboardRankingItem,
} from "./DashboardCompactRankingCard";
import { DashboardExecutiveKpiGrid } from "./DashboardExecutiveKpiGrid";
import KPI from "./DashboardKPI";
import { DashboardSectionBlock } from "./DashboardSectionBlock";

type Props = {
  data: IndicadoresNoRealizadasResponse | null;
  loading: boolean;
  error: string | null;
};

function isNoHuboLabel(label: string): boolean {
  const n = label.trim().toUpperCase().replace(/_/g, " ");
  return n === "NO HUBO" || n === "NOHUBO";
}

function formatDistritoNombre(nombre: string): string {
  const t = nombre.trim();
  if (t.toLowerCase() === "sin distrito" || t === "SIN_DISTRITO") {
    return "Sin distrito";
  }
  return t;
}

/**
 * No realizadas: por tipo, motivos y distritos desde `/api/indicadores/no-realizadas`.
 */
export function DashboardNoRealizadasSection({ data, loading, error }: Props) {
  const porTipo = data?.por_tipo;
  const showValues = !loading && !error && data != null;
  const sectionLoading = loading && !data;

  const kpiValue = (value: number | undefined): number | string => {
    if (loading) return "…";
    if (!showValues || value == null) return "—";
    return value;
  };

  const totalNoRealizadas = useMemo(() => {
    if (!porTipo) return 0;
    return (
      porTipo.inspeccion +
      porTipo.reinspeccion_oficio +
      porTipo.reinspeccion_notificacion +
      porTipo.denuncia
    );
  }, [porTipo]);

  const topContraproducencias = useMemo<DashboardRankingItem[]>(
    () =>
      (data?.top_contraproducencias ?? [])
        .filter((r) => !isNoHuboLabel(r.contraproducencia))
        .map((r) => ({
          label: r.contraproducencia,
          value: r.cantidad,
        })),
    [data?.top_contraproducencias]
  );

  const distritosRanking = useMemo<DashboardRankingItem[]>(
    () =>
      (data?.distritos_con_mas_no_realizadas ?? []).map((d) => ({
        label: formatDistritoNombre(d.distrito_nombre),
        value: d.cantidad,
      })),
    [data?.distritos_con_mas_no_realizadas]
  );

  return (
    <DashboardSectionBlock title="No realizadas">
      {error ? (
        <Alert severity="warning" sx={{ ...alertBaseStyles, mb: 1.25 }}>
          {error}
        </Alert>
      ) : null}

      <DashboardExecutiveKpiGrid
        columns={{ xs: "1fr 1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)", lg: "repeat(5, 1fr)" }}
      >
        <KPI compact title="Total no realizadas" value={kpiValue(showValues ? totalNoRealizadas : undefined)} />
        <KPI compact title="Inspección" value={kpiValue(porTipo?.inspeccion)} />
        <KPI compact title="Reins. oficio" value={kpiValue(porTipo?.reinspeccion_oficio)} />
        <KPI
          compact
          title="Reins. notificación"
          value={kpiValue(porTipo?.reinspeccion_notificacion)}
        />
        <KPI compact title="Denuncia" value={kpiValue(porTipo?.denuncia)} />
      </DashboardExecutiveKpiGrid>

      <Grid container spacing={1.5} sx={{ mt: 0.25 }}>
        <Grid size={{ xs: 12, md: 6 }}>
          <DashboardCompactRankingCard
            title="Motivos de no realización"
            items={topContraproducencias}
            loading={sectionLoading}
            emptyMessage="Sin contraproducencias registradas en el período."
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <DashboardCompactRankingCard
            title="Distritos con más no realizadas"
            items={distritosRanking}
            loading={sectionLoading}
            emptyMessage="Sin no realizadas agrupadas por distrito para el período seleccionado."
          />
        </Grid>
      </Grid>
    </DashboardSectionBlock>
  );
}
