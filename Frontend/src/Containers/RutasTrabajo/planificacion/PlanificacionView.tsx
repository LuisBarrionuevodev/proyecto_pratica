import { useCallback, useEffect, useMemo, useState } from "react";
import { Box, Grid } from "@mui/material";

import type { IRutaIniciadorPendienteRow, IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import {
  usePlanificacionController,
  type PlanificacionPoolControl,
} from "./hooks/usePlanificacionController";
import { PlanificacionHeader } from "./PlanificacionHeader";
import { PlanificacionMapaDistritos } from "./PlanificacionMapaDistritos";
import { PendientesContextoPanel } from "./PendientesContextoPanel";
import { PlanificacionSummaryCards } from "./PlanificacionSummaryCards";
import { PoolDelDiaPanel } from "./PoolDelDiaPanel";
import { UrgentesPanel } from "./UrgentesPanel";

export type PlanificacionViewProps = {
  ruta: IRutaTrabajo;
  rutaId: number;
  onError: (msg: string) => void;
  onContinuarAsignacion: () => void;
  /** Pool del día compartido con Asignación (estado elevado al contenedor del módulo). */
  poolControl: PlanificacionPoolControl;
};

/**
 * Vista Planificación: cards, mapa distrital (M2), urgentes (M3), pendientes contexto (M4), pool local.
 */
export function PlanificacionView({
  ruta,
  rutaId,
  onError,
  onContinuarAsignacion,
  poolControl,
}: PlanificacionViewProps) {
  const ctrl = usePlanificacionController({ rutaId, onError, poolControl });
  const { agregarAlPool } = poolControl;

  const distritoNombreActivo = useMemo(() => {
    if (ctrl.distritoActivoId == null) return null;
    const fromCat = ctrl.distritoCatalogo.find((d) => d.id === ctrl.distritoActivoId)?.nombre;
    if (fromCat) return fromCat;
    const hit = ctrl.cargaPorDistrito.find((c) => c.distrito_id === ctrl.distritoActivoId);
    return hit?.distrito_nombre ?? null;
  }, [ctrl.distritoCatalogo, ctrl.cargaPorDistrito, ctrl.distritoActivoId]);

  const handleApplyBusqueda = useCallback(
    (q: string) => {
      ctrl.setFiltros((f) => ({ ...f, q }));
    },
    [ctrl]
  );

  const handleContinuar = useCallback(() => {
    onContinuarAsignacion();
  }, [onContinuarAsignacion]);

  const [mapPopupRow, setMapPopupRow] = useState<IRutaIniciadorPendienteRow | null>(null);
  const [mapFocusIniciadorId, setMapFocusIniciadorId] = useState<number | null>(null);
  const [mapFlyToRow, setMapFlyToRow] = useState<IRutaIniciadorPendienteRow | null>(null);

  useEffect(() => {
    setMapPopupRow(null);
    setMapFocusIniciadorId(null);
    setMapFlyToRow(null);
  }, [ctrl.distritoActivoId]);

  const handleVerEnMapa = useCallback((row: IRutaIniciadorPendienteRow) => {
    setMapPopupRow(row);
    setMapFocusIniciadorId(row.id);
    setMapFlyToRow(row);
    window.setTimeout(() => setMapFlyToRow(null), 900);
  }, []);

  const handleMapMarkerClick = useCallback((row: IRutaIniciadorPendienteRow) => {
    setMapPopupRow(row);
    setMapFocusIniciadorId(row.id);
  }, []);

  const handleMapPopupClose = useCallback(() => {
    setMapPopupRow(null);
    setMapFocusIniciadorId(null);
  }, []);

  const handleAgregarDesdeMapa = useCallback(
    (row: IRutaIniciadorPendienteRow) => {
      agregarAlPool(row);
      setMapPopupRow(null);
      setMapFocusIniciadorId(null);
    },
    [agregarAlPool]
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, width: "100%", minWidth: 0 }}>
      <PlanificacionHeader ruta={ruta} onContinuarAsignacion={handleContinuar} />

      <PlanificacionSummaryCards
        metricas={ctrl.metricas}
        cardActiva={ctrl.cardActiva}
        onCardChange={ctrl.setCardActiva}
        loading={ctrl.loading.metricas || ctrl.loading.metricasInicial}
      />

      <Grid
        container
        spacing={2}
        sx={{
          alignItems: "stretch",
          minHeight: 480,
          maxHeight: "min(82vh, 880px)",
          minWidth: 0,
        }}
      >
        <Grid size={{ xs: 12, lg: 3 }} sx={{ display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0 }}>
          <PendientesContextoPanel
            distritoActivoId={ctrl.distritoActivoId}
            distritoNombre={distritoNombreActivo}
            filtros={ctrl.filtros}
            onFiltrosChange={(patch) => ctrl.setFiltros((f) => ({ ...f, ...patch }))}
            rows={ctrl.pendientesContextoVisibles}
            meta={ctrl.pendientesMeta}
            loading={ctrl.loading.pendientesContexto}
            onApplyBusqueda={handleApplyBusqueda}
            onPageChange={ctrl.loadPendientesContextoPage}
            onAgregar={ctrl.agregarAlPool}
            onVerEnMapa={handleVerEnMapa}
          />
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }} sx={{ display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0 }}>
          <PlanificacionMapaDistritos
            cargaPorDistrito={ctrl.cargaPorDistrito}
            distritoCatalogo={ctrl.distritoCatalogo}
            loadingCatalogo={ctrl.loadingDistritoCatalogo}
            distritoActivoId={ctrl.distritoActivoId}
            distritoActivoNombre={distritoNombreActivo}
            onSelectDistrito={ctrl.seleccionarDistrito}
            pendientesParaMapa={ctrl.pendientesParaMapa}
            mapFocusIniciadorId={mapFocusIniciadorId}
            mapPopupRow={mapPopupRow}
            mapFlyToRow={mapFlyToRow}
            onMapMarkerClick={handleMapMarkerClick}
            onMapPopupClose={handleMapPopupClose}
            onAgregarDesdeMapa={handleAgregarDesdeMapa}
          />
        </Grid>
        <Grid
          size={{ xs: 12, lg: 3 }}
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 2,
            minWidth: 0,
            minHeight: 0,
            maxHeight: "min(78vh, 820px)",
          }}
        >
          <UrgentesPanel
            rows={ctrl.urgentesVisibles}
            loading={ctrl.loading.urgentes}
            onAgregar={ctrl.agregarAlPool}
            meta={ctrl.urgentesMeta}
            onPageChange={(p) => void ctrl.loadUrgentes(p, ctrl.urgentesMeta.perPage)}
          />
          <PoolDelDiaPanel
            items={ctrl.poolItemsOrdenados}
            onQuitar={ctrl.quitarDelPool}
            onContinuarAsignacion={handleContinuar}
          />
        </Grid>
      </Grid>
    </Box>
  );
}
