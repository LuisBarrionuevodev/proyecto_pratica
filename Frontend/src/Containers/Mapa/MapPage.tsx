import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Snackbar, Stack } from "@mui/material";
import Grid from "@mui/material/Grid";

import { fetchInspectores, type CatalogItem } from "../../api/gridApi";
import { setGeoManual } from "../../api/geoApi";
import { getCurrentMonthRange } from "../../utils/dateRange";
import { alertBaseStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { MapaCanvas, type RelocalOperativoDraft } from "./Components/MapaCanvas";
import { MapaFiltrosUnificados } from "./Components/MapaFiltrosUnificados";
import { MapaModoTabs } from "./Components/MapaModoTabs";
import { PanelResumenOperativo } from "./Components/PanelResumenOperativo";
import { useMapaOperativo } from "./hooks/useMapaOperativo";
import { buildDistritoSelectOptions } from "./utils/distritoOptions";

/**
 * Vista mapa operativo DIGITALIZA: modos Pendientes / Realizados, filtros institucionales y mapa Leaflet.
 */
const MapPage = () => {
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);

  const [modo, setModo] = useState<"pendientes" | "realizados">("pendientes");
  const [fechaDesde, setFechaDesde] = useState(defaultRange.desde);
  const [fechaHasta, setFechaHasta] = useState(defaultRange.hasta);
  const [distritoId, setDistritoId] = useState("");

  const [pendienteTipo, setPendienteTipo] = useState("TODOS");
  const [realizadoTipoIniciador, setRealizadoTipoIniciador] = useState("TODOS");
  const [realizadoDefinicion, setRealizadoDefinicion] = useState("TODOS");
  const [inspectorId, setInspectorId] = useState("");

  const [mapExpanded, setMapExpanded] = useState(false);
  const [inspectores, setInspectores] = useState<CatalogItem[]>([]);

  const [relocalDraft, setRelocalDraft] = useState<RelocalOperativoDraft | null>(null);
  const [relocalGuardando, setRelocalGuardando] = useState(false);
  const [snackbar, setSnackbar] = useState<{ message: string; severity: "success" | "error" } | null>(null);

  const distritoOptions = useMemo(() => buildDistritoSelectOptions(), []);

  const {
    features,
    loading,
    error,
    infoMessage,
    loadPendientes,
    loadRealizados,
  } = useMapaOperativo();

  const filtrosMapa = useMemo(
    () => ({
      from: fechaDesde,
      to: fechaHasta,
      distritoId,
      inspectorId,
    }),
    [fechaDesde, fechaHasta, distritoId, inspectorId]
  );

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await fetchInspectores();
        setInspectores(resp.items ?? []);
      } catch {
        setInspectores([]);
      }
    };
    void load();
  }, []);

  useEffect(() => {
    if (modo === "pendientes") {
      void loadPendientes({ ...filtrosMapa, tipo: pendienteTipo });
    } else {
      void loadRealizados({ ...filtrosMapa, tipo: realizadoTipoIniciador });
    }
  }, [
    modo,
    loadPendientes,
    loadRealizados,
    filtrosMapa,
    pendienteTipo,
    realizadoTipoIniciador,
  ]);

  const handleAplicar = useCallback(() => {
    if (modo === "pendientes") {
      void loadPendientes({ ...filtrosMapa, tipo: pendienteTipo });
      return;
    }
    void loadRealizados({ ...filtrosMapa, tipo: realizadoTipoIniciador });
  }, [
    modo,
    loadPendientes,
    loadRealizados,
    filtrosMapa,
    pendienteTipo,
    realizadoTipoIniciador,
  ]);

  const handleModoChange = useCallback((m: "pendientes" | "realizados") => {
    setModo(m);
    setMapExpanded(false);
    setRelocalDraft(null);
  }, []);

  useEffect(() => {
    setRelocalDraft(null);
  }, [fechaDesde, fechaHasta, distritoId, inspectorId, pendienteTipo, realizadoTipoIniciador]);

  const reloadOperativoActual = useCallback(async () => {
    if (modo === "pendientes") {
      await loadPendientes({ ...filtrosMapa, tipo: pendienteTipo });
    } else {
      await loadRealizados({ ...filtrosMapa, tipo: realizadoTipoIniciador });
    }
  }, [modo, loadPendientes, loadRealizados, filtrosMapa, pendienteTipo, realizadoTipoIniciador]);

  const handleIniciarRelocalizacion = useCallback((payload: RelocalOperativoDraft) => {
    setRelocalDraft({ ...payload });
  }, []);

  const handleRelocalDraftMove = useCallback((lat: number, lng: number) => {
    setRelocalDraft((d) => (d ? { ...d, lat, lng } : null));
  }, []);

  const handleCancelarRelocalizacion = useCallback(() => {
    setRelocalDraft(null);
  }, []);

  const handleConfirmarRelocalizacion = useCallback(async () => {
    if (!relocalDraft) return;
    setRelocalGuardando(true);
    try {
      await setGeoManual(relocalDraft.domicilio_id, relocalDraft.lat, relocalDraft.lng);
      setRelocalDraft(null);
      setSnackbar({
        message: "Ubicación guardada. El mapa y el panel se actualizan con el nuevo geocode del domicilio.",
        severity: "success",
      });
      await reloadOperativoActual();
    } catch (e: unknown) {
      const detail =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setSnackbar({
        message: typeof detail === "string" ? detail : "No se pudo guardar la ubicación.",
        severity: "error",
      });
    } finally {
      setRelocalGuardando(false);
    }
  }, [relocalDraft, reloadOperativoActual]);

  return (
    <Stack
      spacing={2}
      sx={{
        width: "100%",
        maxWidth: "100%",
        boxSizing: "border-box",
        px: { xs: 1, sm: 2 },
        py: 2,
      }}
    >
      {error && (
        <Alert severity="error" sx={alertBaseStyles}>
          {error}
        </Alert>
      )}
      {infoMessage && (
        <Alert severity="info" sx={alertBaseStyles}>
          {infoMessage}
        </Alert>
      )}

      <MapaModoTabs modo={modo} onModoChange={handleModoChange} />

      <MapaFiltrosUnificados
        modo={modo}
        fechaDesde={fechaDesde}
        fechaHasta={fechaHasta}
        onFechaDesdeChange={setFechaDesde}
        onFechaHastaChange={setFechaHasta}
        distritoId={distritoId}
        onDistritoIdChange={setDistritoId}
        distritoOptions={distritoOptions}
        pendienteTipo={pendienteTipo}
        onPendienteTipoChange={setPendienteTipo}
        realizadoTipoIniciador={realizadoTipoIniciador}
        onRealizadoTipoIniciadorChange={setRealizadoTipoIniciador}
        realizadoDefinicion={realizadoDefinicion}
        onRealizadoDefinicionChange={setRealizadoDefinicion}
        inspectorId={inspectorId}
        onInspectorIdChange={setInspectorId}
        inspectores={inspectores}
        onAplicar={handleAplicar}
      />

      <Grid container spacing={2}>
        {!mapExpanded && (
          <Grid size={{ xs: 12, md: 4 }} sx={{ order: { xs: 2, md: 1 } }}>
            <PanelResumenOperativo modo={modo} features={features} />
          </Grid>
        )}
        <Grid size={{ xs: 12, md: mapExpanded ? 12 : 8 }} sx={{ order: { xs: 1, md: 2 } }}>
          <MapaCanvas
            modo={modo}
            features={features}
            loading={loading}
            mapExpanded={mapExpanded}
            onToggleExpand={() => setMapExpanded((e) => !e)}
            relocalDraft={modo === "pendientes" ? relocalDraft : null}
            onRelocalDraftMove={handleRelocalDraftMove}
            onIniciarRelocalizacion={handleIniciarRelocalizacion}
            onCancelarRelocalizacion={handleCancelarRelocalizacion}
            onConfirmarRelocalizacion={handleConfirmarRelocalizacion}
            relocalGuardando={relocalGuardando}
          />
        </Grid>
      </Grid>

      <Snackbar
        open={Boolean(snackbar)}
        autoHideDuration={6000}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        {snackbar ? (
          <Alert severity={snackbar.severity} onClose={() => setSnackbar(null)} sx={{ width: "100%" }} variant="filled">
            {snackbar.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Stack>
  );
};

export default MapPage;
