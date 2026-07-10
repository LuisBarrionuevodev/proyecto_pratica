import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Alert, Stack } from "@mui/material";
import Grid from "@mui/material/Grid";
import { useSearchParams } from "react-router-dom";

import { fetchDistritosCatalogo } from "../../api/geolocalizacionApi";
import { fetchInspectores, type CatalogItem } from "../../api/gridApi";
import { getCurrentMonthRange } from "../../utils/dateRange";
import { alertBaseStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { functionalPageShellSx } from "../../styles/functionalPageShell";
import { MapaCanvas } from "./Components/MapaCanvas";
import { MapaFiltrosUnificados } from "./Components/MapaFiltrosUnificados";
import { MapaModoTabs, type MapaModo } from "./Components/MapaModoTabs";
import { PanelResumenOperativo } from "./Components/PanelResumenOperativo";
import { useMapaOperativo, type MapaOperativoLoadOptions } from "./hooks/useMapaOperativo";
import { MapaDomiciliosGeolocalizacionView } from "./views/MapaDomiciliosGeolocalizacion";

function parseMapaModo(raw: string | null): MapaModo {
  if (raw === "realizados") return "realizados";
  if (raw === "geolocalizacion" || raw === "pendientes") return "geolocalizacion";
  return "geolocalizacion";
}

/**
 * Vista mapa DIGITALIZA: Geolocalización de domicilios (PR6C) y Realizados operativos.
 */
const MapPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);

  const [modo, setModo] = useState<MapaModo>(() => parseMapaModo(searchParams.get("modo")));
  const [fechaDesde, setFechaDesde] = useState(defaultRange.desde);
  const [fechaHasta, setFechaHasta] = useState(defaultRange.hasta);
  const [distritoId, setDistritoId] = useState("");

  const [realizadoTipoIniciador, setRealizadoTipoIniciador] = useState("TODOS");
  const [realizadoDefinicion, setRealizadoDefinicion] = useState("TODOS");
  const [inspectorId, setInspectorId] = useState("");

  const [mapExpanded, setMapExpanded] = useState(false);
  const [inspectores, setInspectores] = useState<CatalogItem[]>([]);

  const [distritoOptions, setDistritoOptions] = useState<{ value: string; label: string }[]>([
    { value: "", label: "Todos los distritos" },
  ]);

  const { features, loading, error, infoMessage, loadRealizados } = useMapaOperativo();

  const filtrosMapa = useMemo(
    () => ({
      from: fechaDesde,
      to: fechaHasta,
      distritoId,
      inspectorId,
    }),
    [fechaDesde, fechaHasta, distritoId, inspectorId]
  );

  const loadParamsRealizados = useMemo(
    () => ({
      ...filtrosMapa,
      tipo: realizadoTipoIniciador,
      definicion: realizadoDefinicion,
    }),
    [filtrosMapa, realizadoTipoIniciador, realizadoDefinicion]
  );

  const filtrosUiRef = useRef({
    from: fechaDesde,
    to: fechaHasta,
    distritoId,
    inspectorId,
    realizadoTipoIniciador,
    realizadoDefinicion,
  });
  filtrosUiRef.current = {
    from: fechaDesde,
    to: fechaHasta,
    distritoId,
    inspectorId,
    realizadoTipoIniciador,
    realizadoDefinicion,
  };

  useEffect(() => {
    const urlModo = parseMapaModo(searchParams.get("modo"));
    setModo(urlModo);
  }, [searchParams]);

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
    if (modo === "realizados") {
      void loadRealizados(loadParamsRealizados);
    }
  }, [modo, loadRealizados, loadParamsRealizados]);

  const handleAplicar = useCallback(() => {
    void loadRealizados(loadParamsRealizados);
  }, [loadRealizados, loadParamsRealizados]);

  const handleModoChange = useCallback(
    (m: MapaModo) => {
      setModo(m);
      setMapExpanded(false);
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (m === "geolocalizacion") {
            next.delete("modo");
          } else {
            next.set("modo", m);
          }
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );

  const cargarRealizadosConSnapshotUi = useCallback(
    async (opts?: MapaOperativoLoadOptions) => {
      const s = filtrosUiRef.current;
      await loadRealizados(
        {
          from: s.from,
          to: s.to,
          distritoId: s.distritoId,
          inspectorId: s.inspectorId,
          tipo: s.realizadoTipoIniciador,
          definicion: s.realizadoDefinicion,
        },
        opts
      );
    },
    [loadRealizados]
  );

  const refrescarOperativoDesdeFormulario = useCallback(() => {
    queueMicrotask(() => {
      void cargarRealizadosConSnapshotUi({ forceNetwork: true });
    });
  }, [cargarRealizadosConSnapshotUi]);

  return (
    <Stack sx={functionalPageShellSx}>
      {modo === "realizados" && error && (
        <Alert severity="error" sx={alertBaseStyles}>
          {error}
        </Alert>
      )}
      {modo === "realizados" && infoMessage && (
        <Alert severity="info" sx={alertBaseStyles}>
          {infoMessage}
        </Alert>
      )}

      <MapaModoTabs modo={modo} onModoChange={handleModoChange} />

      {modo === "geolocalizacion" ? (
        <MapaDomiciliosGeolocalizacionView
          title="Mapa"
          subtitle="Geolocalización de domicilios"
          showHeader={false}
          filterVariant="mapa"
          actionVariant="icon"
          showDetailPanel={false}
          defaultStatus="requiere_accion"
        />
      ) : (
        <>
          <MapaFiltrosUnificados
            fechaDesde={fechaDesde}
            fechaHasta={fechaHasta}
            onFechaDesdeChange={setFechaDesde}
            onFechaHastaChange={setFechaHasta}
            distritoId={distritoId}
            onDistritoIdChange={setDistritoId}
            distritoOptions={distritoOptions}
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
                <PanelResumenOperativo features={features} />
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
                features={features}
                loading={loading}
                mapExpanded={mapExpanded}
                onToggleExpand={() => setMapExpanded((e) => !e)}
              />
            </Grid>
          </Grid>
        </>
      )}
    </Stack>
  );
};

export default MapPage;
