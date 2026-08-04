import { Alert } from "@mui/material";

import type { IndicadoresEjecutivoResponse } from "../../../api/indicadoresApi";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import {
  DashboardAnalyticsKpiCard,
  type DashboardKpiAccent,
} from "./DashboardAnalyticsKpiCard";
import { DashboardMetricGrid } from "./DashboardMetricGrid";
import { DashboardSectionBlock } from "./DashboardSectionBlock";

type Props = {
  data: IndicadoresEjecutivoResponse | null;
  noRealizadasTotal: number | null;
  loading: boolean;
  error: string | null;
};

const OVERVIEW_ACCENTS: DashboardKpiAccent[] = [
  "primary",
  "teal",
  "primary",
  "amber",
  "teal",
  "primary",
  "amber",
  "neutral",
];

/**
 * Overview operativo: KPIs analytics desde `/api/indicadores/ejecutivo` + total no realizadas.
 */
export function DashboardEjecutivoSection({
  data,
  noRealizadasTotal,
  error,
}: Props) {
  const kpis = data?.kpis;

  const kpiValue = (value: number | undefined): number | string => {
    if (error || data == null) return "—";
    if (value == null) return "—";
    return value;
  };

  const cards = [
    { label: "Actuaciones realizadas", value: kpiValue(kpis?.actuaciones_realizadas) },
    { label: "Actas labradas", value: kpiValue(kpis?.actas_labradas) },
    {
      label: "Reins. notificación realizadas",
      value: kpiValue(kpis?.reinspecciones_notificacion_realizadas),
    },
    {
      label: "Reins. oficio realizadas",
      value: kpiValue(kpis?.reinspecciones_oficio_realizadas),
    },
    {
      label: "No realizadas",
      value:
        error || data == null
          ? "—"
          : noRealizadasTotal != null
            ? noRealizadasTotal
            : "—",
    },
    {
      label: "Mercadería decomisada",
      value:
        error || data == null || kpis == null
          ? "—"
          : kpis.mercaderia_decomisada_kg.toLocaleString("es-AR", {
              maximumFractionDigits: 2,
            }),
      unit: error || data == null ? undefined : "kg",
    },
    {
      label: "Ratif. clausura realizadas",
      value: kpiValue(kpis?.ratificaciones_clausura_realizadas),
    },
    {
      label: "Ratif. decomiso realizadas",
      value: kpiValue(kpis?.ratificaciones_decomiso_realizadas),
    },
    {
      label: "Verificar e informar realizadas",
      value: kpiValue(kpis?.verificar_informar_realizadas),
    },
  ];

  return (
    <DashboardSectionBlock first title="Overview operativo">
      {error ? (
        <Alert severity="warning" sx={{ ...alertBaseStyles, mb: 1.25 }}>
          {error}
        </Alert>
      ) : null}

      <DashboardMetricGrid
        columns={{
          xs: "1fr",
          sm: "repeat(2, 1fr)",
          md: "repeat(3, 1fr)",
          lg: "repeat(4, 1fr)",
        }}
        gap={1.5}
      >
        {cards.map((card, idx) => (
          <DashboardAnalyticsKpiCard
            key={card.label}
            label={card.label}
            value={card.value}
            unit={"unit" in card ? card.unit : undefined}
            accent={OVERVIEW_ACCENTS[idx] ?? "neutral"}
          />
        ))}
      </DashboardMetricGrid>
    </DashboardSectionBlock>
  );
}
