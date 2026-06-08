import { Alert, Box, Grid } from "@mui/material";
import { useMemo } from "react";

import type { IndicadoresNoRealizadasResponse } from "../../../api/indicadoresApi";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import { DashboardAnalyticsKpiCard } from "./DashboardAnalyticsKpiCard";
import { DashboardHorizontalBarChartCard } from "./DashboardHorizontalBarChartCard";
import type { DashboardRankingBarItem } from "./DashboardRankingBarList";
import { DashboardMetricGrid } from "./DashboardMetricGrid";
import { DashboardSectionBlock } from "./DashboardSectionBlock";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

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
 * No realizadas: KPIs + rankings en barras horizontales.
 */
export function DashboardNoRealizadasSection({ data, loading, error }: Props) {
  const porTipo = data?.por_tipo;
  const showValues = !loading && !error && data != null;
  const sectionLoading = loading && !data;

  const kpiValue = (value: number | undefined): number | string => {
    if (sectionLoading) return "…";
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

  const topContraproducencias = useMemo<DashboardRankingBarItem[]>(
    () =>
      (data?.top_contraproducencias ?? [])
        .filter((r) => !isNoHuboLabel(r.contraproducencia))
        .map((r) => ({
          label: r.contraproducencia,
          value: r.cantidad,
        })),
    [data?.top_contraproducencias],
  );

  const distritosRanking = useMemo<DashboardRankingBarItem[]>(
    () =>
      (data?.distritos_con_mas_no_realizadas ?? []).map((d) => ({
        label: formatDistritoNombre(d.distrito_nombre),
        value: d.cantidad,
      })),
    [data?.distritos_con_mas_no_realizadas],
  );

  return (
    <DashboardSectionBlock title="No realizadas">
      {error ? (
        <Alert severity="warning" sx={{ ...alertBaseStyles, mb: 1.25 }}>
          {error}
        </Alert>
      ) : null}

      <Box sx={{ mb: 2.5 }}>
      <DashboardMetricGrid
        columns={{ xs: "1fr 1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)", lg: "repeat(5, 1fr)" }}
        gap={1.5}
      >
        <DashboardAnalyticsKpiCard
          label="Total no realizadas"
          value={kpiValue(showValues ? totalNoRealizadas : undefined)}
          loading={sectionLoading}
          accent="amber"
        />
        <DashboardAnalyticsKpiCard
          label="Inspección"
          value={kpiValue(porTipo?.inspeccion)}
          loading={sectionLoading}
          accent="primary"
        />
        <DashboardAnalyticsKpiCard
          label="Reins. oficio"
          value={kpiValue(porTipo?.reinspeccion_oficio)}
          loading={sectionLoading}
          accent="teal"
        />
        <DashboardAnalyticsKpiCard
          label="Reins. notificación"
          value={kpiValue(porTipo?.reinspeccion_notificacion)}
          loading={sectionLoading}
          accent="primary"
        />
        <DashboardAnalyticsKpiCard
          label="Denuncia"
          value={kpiValue(porTipo?.denuncia)}
          loading={sectionLoading}
          accent="neutral"
        />
      </DashboardMetricGrid>
      </Box>

      <Grid container spacing={1.5} alignItems="stretch">
        <Grid size={{ xs: 12, md: 6 }} sx={{ display: "flex" }}>
          <DashboardHorizontalBarChartCard
            title="Motivos de no realización"
            items={topContraproducencias}
            loading={sectionLoading}
            emptyMessage="Sin motivos registrados en el período."
            color="#F5A623"
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }} sx={{ display: "flex" }}>
          <DashboardHorizontalBarChartCard
            title="Distritos con más no realizadas"
            items={distritosRanking}
            loading={sectionLoading}
            emptyMessage="Sin no realizadas por distrito en el período."
            color={GLASS_COLORS.primary}
          />
        </Grid>
      </Grid>
    </DashboardSectionBlock>
  );
}
