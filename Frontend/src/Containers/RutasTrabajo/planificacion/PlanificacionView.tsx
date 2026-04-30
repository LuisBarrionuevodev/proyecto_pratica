import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Box, Grid } from "@mui/material";

import type { IRutaIniciadorPendienteRow, IRutaTrabajo } from "../../../api/rutasTrabajoApi";
import {
  usePlanificacionController,
  type PlanificacionPoolControl,
} from "./hooks/usePlanificacionController";

import { AppButton } from "../../../ui";
import { RutaResumenHeaderCard, rutaResumenHeaderAccionButtonSx } from "../Components/RutaResumenHeaderCard";
import { estadoRutaVisible, turnoLabel } from "../utils/rutaResumenLabels";
import { PlanificacionMapaDistritos } from "./PlanificacionMapaDistritos";
import { PendientesContextoPanel } from "./PendientesContextoPanel";
import { PlanificacionSummaryCards } from "./PlanificacionSummaryCards";
import { PoolDelDiaPanel } from "./PoolDelDiaPanel";
import { UrgentesPanel } from "./UrgentesPanel";
import { parseIniciadorLatLng } from "./utils/iniciadorCoords";

export type PlanificacionViewProps = {
  ruta: IRutaTrabajo;
  rutaId: number;
  onError: (msg: string) => void;
  /** Vuelve a la prepantalla (lista de borradores / crear ruta). */
  onVolverAElegirRuta: () => void;
  onContinuarAsignacion: () => void;
  /** Pool del día compartido con Asignación (estado elevado al contenedor del módulo). */
  poolControl: PlanificacionPoolControl;
};

const PENDING_VER_MAPA_MS = 12_000;

function distritoIdRow(row: IRutaIniciadorPendienteRow): number | null {
  const a = row.distrito_id ?? null;
  if (typeof a === "number" && Number.isFinite(a)) return a;
  const b = row.domicilio?.distrito_id ?? null;
  if (typeof b === "number" && Number.isFinite(b)) return b;
  return null;
}

/**
 * Vista Planificación: cards, mapa distrital (M2), urgentes (M3), pendientes contexto (M4), pool local.
 */
export function PlanificacionView({
  ruta,
  rutaId,
  onError,
  onVolverAElegirRuta,
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
  const [mapPopupOpenNonce, setMapPopupOpenNonce] = useState(0);
  const [pendingVerEnMapaRow, setPendingVerEnMapaRow] = useState<IRutaIniciadorPendienteRow | null>(null);

  const preservingPendingOnNextDistritoChangeRef = useRef<number | null>(null);
  const pendingMapTimeoutRef = useRef<ReturnType<typeof window.setTimeout> | null>(null);

  const clearPendingMapTimeout = useCallback(() => {
    if (pendingMapTimeoutRef.current != null) {
      window.clearTimeout(pendingMapTimeoutRef.current);
      pendingMapTimeoutRef.current = null;
    }
  }, []);

  const handleReiniciarPendientesContexto = useCallback(() => {
    ctrl.reiniciarFiltrosPendientesContexto();
    clearPendingMapTimeout();
    setPendingVerEnMapaRow(null);
    setMapPopupRow(null);
    setMapFocusIniciadorId(null);
    setMapFlyToRow(null);
  }, [ctrl, clearPendingMapTimeout]);

  const bumpPopupNonce = useCallback(() => {
    setMapPopupOpenNonce((n) => n + 1);
  }, []);

  const applyMapFocus = useCallback(
    (row: IRutaIniciadorPendienteRow) => {
      clearPendingMapTimeout();
      setPendingVerEnMapaRow(null);
      setMapPopupRow(row);
      setMapFocusIniciadorId(row.id);
      setMapFlyToRow(row);
      bumpPopupNonce();
      window.setTimeout(() => setMapFlyToRow(null), 900);
    },
    [bumpPopupNonce, clearPendingMapTimeout]
  );

  const schedulePendingTimeout = useCallback(
    (rowId: number) => {
      clearPendingMapTimeout();
      pendingMapTimeoutRef.current = window.setTimeout(() => {
        pendingMapTimeoutRef.current = null;
        setPendingVerEnMapaRow((prev) => {
          if (prev?.id !== rowId) return prev;
          onError("No se pudo centrar el punto en el mapa. Revisá el distrito o la geocodificación.");
          return null;
        });
      }, PENDING_VER_MAPA_MS);
    },
    [clearPendingMapTimeout, onError]
  );

  useEffect(() => {
    setMapPopupRow(null);
    setMapFocusIniciadorId(null);
    setMapFlyToRow(null);
    const preserveId = preservingPendingOnNextDistritoChangeRef.current;
    preservingPendingOnNextDistritoChangeRef.current = null;
    if (preserveId == null) {
      setPendingVerEnMapaRow(null);
      clearPendingMapTimeout();
    }
  }, [ctrl.distritoActivoId, clearPendingMapTimeout]);

  useEffect(() => {
    if (!pendingVerEnMapaRow) return;
    const id = pendingVerEnMapaRow.id;
    const match = ctrl.pendientesParaMapa.find((r) => r.id === id);
    if (!match || !parseIniciadorLatLng(match)) return;

    applyMapFocus(match);
  }, [pendingVerEnMapaRow, ctrl.pendientesParaMapa, applyMapFocus]);

  useEffect(
    () => () => {
      clearPendingMapTimeout();
    },
    [clearPendingMapTimeout]
  );

  const handleVerEnMapa = useCallback(
    (row: IRutaIniciadorPendienteRow) => {
      if (!parseIniciadorLatLng(row)) return;

      const targetDistritoId = distritoIdRow(row);

      if (targetDistritoId == null) {
        if (ctrl.distritoActivoId == null) {
          onError("Elegí un distrito en el mapa para ver puntos.");
          return;
        }
        const inLayer = ctrl.pendientesParaMapa.some((r) => r.id === row.id && parseIniciadorLatLng(r));
        if (inLayer) {
          const fresh = ctrl.pendientesParaMapa.find((r) => r.id === row.id);
          if (fresh) applyMapFocus(fresh);
        } else {
          onError(
            "Este pendiente no aparece en el mapa del distrito activo. Cambiá de distrito o verificá la geocodificación."
          );
        }
        return;
      }

      if (targetDistritoId !== ctrl.distritoActivoId) {
        preservingPendingOnNextDistritoChangeRef.current = row.id;
        ctrl.seleccionarDistrito(targetDistritoId);
        setPendingVerEnMapaRow(row);
        schedulePendingTimeout(row.id);
        return;
      }

      const fresh = ctrl.pendientesParaMapa.find((r) => r.id === row.id);
      if (fresh && parseIniciadorLatLng(fresh)) {
        applyMapFocus(fresh);
      } else {
        setPendingVerEnMapaRow(row);
        schedulePendingTimeout(row.id);
      }
    },
    [
      ctrl.distritoActivoId,
      ctrl.pendientesParaMapa,
      ctrl.seleccionarDistrito,
      onError,
      applyMapFocus,
      schedulePendingTimeout,
    ]
  );

  const handleMapMarkerClick = useCallback((row: IRutaIniciadorPendienteRow) => {
    setMapPopupRow(row);
    setMapFocusIniciadorId(row.id);
    bumpPopupNonce();
  }, [bumpPopupNonce]);

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
      <RutaResumenHeaderCard
        title="Resumen de ruta"
        chips={[
          ...(estadoRutaVisible(ruta.estado_ruta)
            ? [{ key: "estado", label: estadoRutaVisible(ruta.estado_ruta)!, variant: "estado" as const }]
            : []),
          { key: "fecha", label: ruta.fecha },
          { key: "turno", label: turnoLabel(ruta.turno) },
        ]}
        actions={
          <>
            <AppButton
              dsVariant="secondary"
              dsSize="md"
              fullWidth
              startIcon={<ArrowBackIcon />}
              onClick={onVolverAElegirRuta}
              sx={{ ...rutaResumenHeaderAccionButtonSx, fontWeight: 600 }}
            >
              Elegir otra ruta
            </AppButton>
            <AppButton
              dsVariant="primary"
              dsSize="md"
              fullWidth
              onClick={handleContinuar}
              sx={{ ...rutaResumenHeaderAccionButtonSx, fontWeight: 700 }}
            >
              Continuar a asignación
            </AppButton>
          </>
        }
      />

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
            onReiniciarContextoPanel={handleReiniciarPendientesContexto}
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
            mapPopupOpenNonce={mapPopupOpenNonce}
            onMapMarkerClick={handleMapMarkerClick}
            onMapPopupClose={handleMapPopupClose}
            onAgregarDesdeMapa={handleAgregarDesdeMapa}
            poolIniciadorIds={poolControl.poolIniciadorIds}
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
            ocultosPorPoolEnPagina={ctrl.urgentesOcultosPorPoolEnPagina}
            onPageChange={(p) => void ctrl.loadUrgentes(p, ctrl.urgentesMeta.perPage)}
            onVerEnMapa={handleVerEnMapa}
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
