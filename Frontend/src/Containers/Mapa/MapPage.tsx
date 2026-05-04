import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Alert, Snackbar, Stack } from "@mui/material";
import Grid from "@mui/material/Grid";

import { fetchDistritosCatalogo } from "../../api/geolocalizacionApi";
import { fetchInspectores, type CatalogItem } from "../../api/gridApi";
import { setGeoManual } from "../../api/geoApi";
import { getCurrentMonthRange } from "../../utils/dateRange";
import { alertBaseStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { MapaCanvas, type RelocalOperativoDraft } from "./Components/MapaCanvas";
import { MapaFiltrosUnificados } from "./Components/MapaFiltrosUnificados";
import { MapaModoTabs } from "./Components/MapaModoTabs";
import { PanelResumenOperativo } from "./Components/PanelResumenOperativo";
import { useMapaOperativo, type MapaOperativoLoadOptions } from "./hooks/useMapaOperativo";

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

  const [distritoOptions, setDistritoOptions] = useState<{ value: string; label: string }[]>([
    { value: "", label: "Todos los distritos" },
  ]);

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

  const loadParamsPendientes = useMemo(
    () => ({ ...filtrosMapa, tipo: pendienteTipo }),
    [filtrosMapa, pendienteTipo]
  );

  const loadParamsRealizados = useMemo(
    () => ({
      ...filtrosMapa,
      tipo: realizadoTipoIniciador,
      definicion: realizadoDefinicion,
    }),
    [filtrosMapa, realizadoTipoIniciador, realizadoDefinicion]
  );

  /**
   * Snapshot síncrono de lo que muestra el formulario (un solo ref, actualizado cada render).
   * Refrescar lee esto tras un microtask para alinear con commits recientes de React.
   */
  const filtrosUiRef = useRef({
    modo,
    from: fechaDesde,
    to: fechaHasta,
    distritoId,
    inspectorId,
    pendienteTipo,
    realizadoTipoIniciador,
    realizadoDefinicion,
  });
  filtrosUiRef.current = {
    modo,
    from: fechaDesde,
    to: fechaHasta,
    distritoId,
    inspectorId,
    pendienteTipo,
    realizadoTipoIniciador,
    realizadoDefinicion,
  };

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
    let cancelled = false;
    void fetchDistritosCatalogo()
      .then((resp) => {
        if (cancelled) return;
        setDistritoOptions([
          { value: "", label: "Todos los distritos" },
          ...(resp.items ?? []).map((d) => ({ value: String(d.id), label: d.nombre })),
        ]);
      })
      .catch(() => {
        if (!cancelled) {
          setDistritoOptions([{ value: "", label: "Todos los distritos" }]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (distritoOptions.length <= 1) return;
    if (distritoId && !distritoOptions.some((o) => o.value === distritoId)) {
      setDistritoId("");
    }
  }, [distritoOptions, distritoId]);

  useEffect(() => {
    if (modo === "pendientes") {
      void loadPendientes(loadParamsPendientes);
    } else {
      void loadRealizados(loadParamsRealizados);
    }
  }, [modo, loadPendientes, loadRealizados, loadParamsPendientes, loadParamsRealizados]);

  const handleAplicar = useCallback(() => {
    if (modo === "pendientes") {
      void loadPendientes(loadParamsPendientes);
      return;
    }
    void loadRealizados(loadParamsRealizados);
  }, [modo, loadPendientes, loadRealizados, loadParamsPendientes, loadParamsRealizados]);

  const handleModoChange = useCallback((m: "pendientes" | "realizados") => {
    setModo(m);
    setMapExpanded(false);
    setRelocalDraft(null);
    if (m === "pendientes") {
      setInspectorId("");
    }
  }, []);

  useEffect(() => {
    setRelocalDraft(null);
  }, [
    fechaDesde,
    fechaHasta,
    distritoId,
    inspectorId,
    pendienteTipo,
    realizadoTipoIniciador,
    realizadoDefinicion,
  ]);

  const cargarOperativoConSnapshotUi = useCallback(async (opts?: MapaOperativoLoadOptions) => {
    const s = filtrosUiRef.current;
    const base = {
      from: s.from,
      to: s.to,
      distritoId: s.distritoId,
      inspectorId: s.modo === "pendientes" ? "" : s.inspectorId,
    };
    if (s.modo === "pendientes") {
      await loadPendientes({ ...base, tipo: s.pendienteTipo }, opts);
    } else {
      await loadRealizados(
        { ...base, tipo: s.realizadoTipoIniciador, definicion: s.realizadoDefinicion },
        opts
      );
    }
  }, [loadPendientes, loadRealizados]);

  const refrescarOperativoDesdeFormulario = useCallback(() => {
    queueMicrotask(() => {
      void cargarOperativoConSnapshotUi({ forceNetwork: true });
    });
  }, [cargarOperativoConSnapshotUi]);

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
      await cargarOperativoConSnapshotUi();
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
  }, [relocalDraft, cargarOperativoConSnapshotUi]);

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
        onRefrescar={refrescarOperativoDesdeFormulario}
      />

      <Grid
        container
        spacing={2}
        sx={
          mapExpanded
            ? {
                alignItems: "stretch",
                minHeight: { xs: "72vh", md: "min(92vh, 960px)" },
              }
            : undefined
        }
      >
        {!mapExpanded && (
          <Grid size={{ xs: 12, md: 4 }} sx={{ order: { xs: 2, md: 1 } }}>
            <PanelResumenOperativo modo={modo} features={features} />
          </Grid>
        )}
        <Grid
          size={{ xs: 12, md: mapExpanded ? 12 : 8 }}
          sx={{
            order: { xs: 1, md: 2 },
            display: "flex",
            flexDirection: "column",
            minHeight: mapExpanded ? { xs: "72vh", md: "min(92vh, 960px)" } : undefined,
            flex: mapExpanded ? 1 : undefined,
          }}
        >
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
