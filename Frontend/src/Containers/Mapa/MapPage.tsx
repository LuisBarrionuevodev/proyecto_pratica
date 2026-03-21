import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Stack } from "@mui/material";
import Grid from "@mui/material/Grid";

import { fetchInspectores, type CatalogItem } from "../../api/gridApi";
import { getCurrentMonthRange } from "../../utils/dateRange";
import { alertBaseStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { MapaCanvas } from "./components/MapaCanvas";
import { MapaFiltrosUnificados } from "./components/MapaFiltrosUnificados";
import { MapaModoTabs } from "./components/MapaModoTabs";
import { PanelResumenOperativo } from "./components/PanelResumenOperativo";
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

  const distritoOptions = useMemo(() => buildDistritoSelectOptions(), []);

  const {
    features,
    loading,
    error,
    infoMessage,
    loadPendientes,
    loadRealizados,
    clearForModoSwitch,
  } = useMapaOperativo();

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
    clearForModoSwitch();
    if (modo === "pendientes") {
      loadPendientes();
    }
  }, [modo, clearForModoSwitch, loadPendientes]);

  const handleAplicar = useCallback(() => {
    if (modo === "pendientes") {
      loadPendientes();
      return;
    }
    void loadRealizados({
      from: fechaDesde,
      to: fechaHasta,
      distritoId,
      tipoIniciador: realizadoTipoIniciador,
    });
  }, [modo, loadPendientes, loadRealizados, fechaDesde, fechaHasta, distritoId, realizadoTipoIniciador]);

  const handleModoChange = useCallback((m: "pendientes" | "realizados") => {
    setModo(m);
    setMapExpanded(false);
  }, []);

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
      {infoMessage && modo === "pendientes" && (
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
          />
        </Grid>
      </Grid>
    </Stack>
  );
};

export default MapPage;
