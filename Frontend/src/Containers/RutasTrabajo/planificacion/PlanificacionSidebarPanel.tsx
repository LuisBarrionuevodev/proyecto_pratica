import { useMemo, useState } from "react";
import { Box, Stack, Tab, Tabs, Typography } from "@mui/material";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { GLASS_COLORS, glassSecondaryTabsSx, glassTabsSecondaryPanelBarSx } from "../../../styles/GlassStyles";
import { PlanificacionFiltrosBar } from "./PlanificacionFiltrosBar";
import { PendientesContextoPanel } from "./PendientesContextoPanel";
import { UrgentesPanel } from "./UrgentesPanel";
import { planificacionSidebarShellSx, planificacionSidebarTabBodySx } from "./planificacionMyMapsLayout";
import type {
  IPlanificacionMetricas,
  PlanificacionCardKey,
  PlanificacionFiltrosLista,
  UrgentesFiltrosAplicados,
} from "./types/planificacion.types";

export type PlanificacionSidebarTab = "total-mapa" | "urgentes";

export type PlanificacionSidebarPanelProps = {
  distritoActivoId: number | null;
  metricas: IPlanificacionMetricas | null;
  metricasLoading?: boolean;
  cardActiva: PlanificacionCardKey;
  onCardChange: (card: PlanificacionCardKey) => void;
  filtrosAplicados: PlanificacionFiltrosLista;
  onFiltrarCandidatos: (filtros: PlanificacionFiltrosLista) => void;
  onLimpiarCandidatos: () => void;
  rubroNombre?: string | null;
  candidatosRows: IRutaIniciadorPendienteRow[];
  candidatosMeta: { total: number; page: number; perPage: number };
  candidatosLoading: boolean;
  onCandidatosPageChange: (page: number) => void;
  onAgregarCandidato: (row: IRutaIniciadorPendienteRow) => void;
  onVerEnMapa?: (row: IRutaIniciadorPendienteRow) => void;
  urgentesRows: IRutaIniciadorPendienteRow[];
  urgentesMeta: { total: number; page: number; perPage: number };
  urgentesLoading: boolean;
  urgentesOcultosPorPoolEnPagina?: number;
  onUrgentesPageChange: (page: number) => void;
  onAgregarUrgente: (row: IRutaIniciadorPendienteRow) => void;
  urgentesFiltros: UrgentesFiltrosAplicados;
  onFiltrarUrgentes: (filtros: UrgentesFiltrosAplicados) => void;
  onLimpiarUrgentes: () => void;
};

const TAB_DEFS: { id: PlanificacionSidebarTab; label: string }[] = [
  { id: "total-mapa", label: "Total mapa" },
  { id: "urgentes", label: "Urgentes" },
];

/**
 * Panel lateral OPER-RUTA.7C.1: tabs Total mapa / Urgentes + listado amplio.
 */
export function PlanificacionSidebarPanel({
  distritoActivoId,
  metricas,
  metricasLoading,
  cardActiva,
  onCardChange,
  filtrosAplicados,
  onFiltrarCandidatos,
  onLimpiarCandidatos,
  rubroNombre,
  candidatosRows,
  candidatosMeta,
  candidatosLoading,
  onCandidatosPageChange,
  onAgregarCandidato,
  onVerEnMapa,
  urgentesRows,
  urgentesMeta,
  urgentesLoading,
  urgentesOcultosPorPoolEnPagina,
  onUrgentesPageChange,
  onAgregarUrgente,
  urgentesFiltros,
  onFiltrarUrgentes,
  onLimpiarUrgentes,
}: PlanificacionSidebarPanelProps) {
  const [tab, setTab] = useState<PlanificacionSidebarTab>("total-mapa");

  const urgentesTabLabel = useMemo(() => {
    const base = "Urgentes";
    return urgentesMeta.total > 0 ? `${base} (${urgentesMeta.total})` : base;
  }, [urgentesMeta.total]);

  return (
    <Stack sx={planificacionSidebarShellSx} data-testid="planificacion-sidebar-panel">
      <Typography
        sx={{
          fontFamily: '"Tactic Sans", sans-serif',
          fontWeight: 700,
          fontSize: "0.9375rem",
          color: GLASS_COLORS.textPrimary,
          flexShrink: 0,
        }}
      >
        Planificación
      </Typography>

      <Box sx={glassTabsSecondaryPanelBarSx}>
        <Tabs
          value={tab}
          onChange={(_, v: PlanificacionSidebarTab) => setTab(v)}
          variant="fullWidth"
          sx={glassSecondaryTabsSx}
        >
          {TAB_DEFS.map((t) => (
            <Tab
              key={t.id}
              value={t.id}
              label={t.id === "urgentes" ? urgentesTabLabel : t.label}
              data-testid={`planificacion-tab-${t.id}`}
            />
          ))}
        </Tabs>
      </Box>

      <Box sx={planificacionSidebarTabBodySx}>
        <PlanificacionFiltrosBar
          distritoActivoId={distritoActivoId}
          metricas={metricas}
          cardActiva={cardActiva}
          onCardChange={onCardChange}
          metricasLoading={metricasLoading}
          filtrosAplicados={filtrosAplicados}
          onFiltrarCandidatos={onFiltrarCandidatos}
          onLimpiarCandidatos={onLimpiarCandidatos}
          candidatosLoading={candidatosLoading}
          rubroNombre={rubroNombre}
          sidebarTab={tab}
          urgentesFiltros={urgentesFiltros}
          onFiltrarUrgentes={onFiltrarUrgentes}
          onLimpiarUrgentes={onLimpiarUrgentes}
          urgentesLoading={urgentesLoading}
        />

        {tab === "total-mapa" ? (
          <PendientesContextoPanel
            variant="embedded"
            distritoActivoId={distritoActivoId}
            rows={candidatosRows}
            meta={candidatosMeta}
            loading={candidatosLoading}
            onPageChange={onCandidatosPageChange}
            onAgregar={onAgregarCandidato}
            onVerEnMapa={onVerEnMapa}
          />
        ) : (
          <UrgentesPanel
            variant="embedded"
            rows={urgentesRows}
            loading={urgentesLoading}
            onAgregar={onAgregarUrgente}
            meta={urgentesMeta}
            onPageChange={onUrgentesPageChange}
            ocultosPorPoolEnPagina={urgentesOcultosPorPoolEnPagina}
            onVerEnMapa={onVerEnMapa}
          />
        )}
      </Box>
    </Stack>
  );
}
