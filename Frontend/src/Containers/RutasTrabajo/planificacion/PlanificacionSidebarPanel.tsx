import { useMemo, useState } from "react";
import { Box, Stack, Tab, Tabs, Typography } from "@mui/material";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import type { IRutaPoolDiaRow } from "../../../api/rutaPoolDiaApi";
import { GLASS_COLORS, glassSecondaryTabsSx, glassTabsSecondaryPanelBarSx } from "../../../styles/GlassStyles";
import { AppButton } from "../../../ui";
import { PlanificacionFiltrosBar } from "./PlanificacionFiltrosBar";
import { PendientesContextoPanel } from "./PendientesContextoPanel";
import { PlanificacionResumenPanel } from "./PlanificacionResumenPanel";
import { PoolDelDiaPanel } from "./PoolDelDiaPanel";
import { UrgentesPanel } from "./UrgentesPanel";
import {
  planificacionSidebarFooterSx,
  planificacionSidebarShellSx,
  planificacionSidebarTabBodySx,
} from "./planificacionMyMapsLayout";
import type {
  IPlanificacionMetricas,
  PlanificacionCardKey,
  PlanificacionFiltrosLista,
  UrgentesFiltrosAplicados,
} from "./types/planificacion.types";

export type PlanificacionSidebarTab = "candidatos" | "urgentes" | "pool" | "resumen";

export type PlanificacionSidebarPanelProps = {
  distritoActivoId: number | null;
  distritoNombre?: string | null;
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
  poolItems: IRutaPoolDiaRow[];
  poolLoading?: boolean;
  onQuitarPool: (poolId: number) => void | Promise<void>;
  onContinuarAsignacion: () => void;
};

const TAB_DEFS: { id: PlanificacionSidebarTab; label: string }[] = [
  { id: "candidatos", label: "Candidatos" },
  { id: "urgentes", label: "Urgentes" },
  { id: "pool", label: "Pool" },
  { id: "resumen", label: "Resumen" },
];

/**
 * Panel lateral unificado OPER-RUTA.7C: filtros + tabs + listas compactas + acciones.
 */
export function PlanificacionSidebarPanel({
  distritoActivoId,
  distritoNombre,
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
  poolItems,
  poolLoading,
  onQuitarPool,
  onContinuarAsignacion,
}: PlanificacionSidebarPanelProps) {
  const [tab, setTab] = useState<PlanificacionSidebarTab>("candidatos");

  const poolEnGrupo = useMemo(
    () => poolItems.filter((p) => p.ruta_item_id != null).length,
    [poolItems]
  );
  const poolLibre = poolItems.length - poolEnGrupo;

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

      <PlanificacionFiltrosBar
        distritoActivoId={distritoActivoId}
        distritoNombre={distritoNombre}
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

      <Box sx={glassTabsSecondaryPanelBarSx}>
        <Tabs
          value={tab}
          onChange={(_, v: PlanificacionSidebarTab) => setTab(v)}
          variant="scrollable"
          scrollButtons="auto"
          sx={glassSecondaryTabsSx}
        >
          {TAB_DEFS.map((t) => (
            <Tab
              key={t.id}
              value={t.id}
              label={
                t.id === "pool"
                  ? `${t.label} (${poolItems.length})`
                  : t.id === "urgentes"
                    ? `${t.label} (${urgentesMeta.total})`
                    : t.label
              }
            />
          ))}
        </Tabs>
      </Box>

      <Box sx={planificacionSidebarTabBodySx}>
        {tab === "candidatos" ? (
          <PendientesContextoPanel
            variant="embedded"
            distritoActivoId={distritoActivoId}
            distritoNombre={distritoNombre}
            rows={candidatosRows}
            meta={candidatosMeta}
            loading={candidatosLoading}
            onPageChange={onCandidatosPageChange}
            onAgregar={onAgregarCandidato}
            onVerEnMapa={onVerEnMapa}
          />
        ) : null}

        {tab === "urgentes" ? (
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
        ) : null}

        {tab === "pool" ? (
          <PoolDelDiaPanel
            variant="embedded"
            items={poolItems}
            loading={poolLoading}
            onQuitar={onQuitarPool}
            compact
          />
        ) : null}

        {tab === "resumen" ? (
          <PlanificacionResumenPanel
            poolItems={poolItems}
            candidatosVisibles={candidatosRows.length}
            candidatosTotal={candidatosMeta.total}
            urgentesTotal={urgentesMeta.total}
            poolEnGrupo={poolEnGrupo}
            poolLibre={poolLibre}
            distritoNombre={distritoNombre}
            distritoActivoId={distritoActivoId}
          />
        ) : null}
      </Box>

      <Box sx={planificacionSidebarFooterSx}>
        <AppButton
          dsVariant="primary"
          fullWidth
          onClick={onContinuarAsignacion}
          disabled={poolItems.length === 0}
          data-testid="planificacion-continuar-asignacion"
        >
          Continuar a asignación
        </AppButton>
      </Box>
    </Stack>
  );
}
