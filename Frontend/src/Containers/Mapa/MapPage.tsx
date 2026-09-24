import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Alert, Stack } from "@mui/material";
import Grid from "@mui/material/Grid";
import { useSearchParams } from "react-router-dom";

import { fetchDistritosCatalogo } from "../../api/geolocalizacionApi";
import { fetchInspectores, type CatalogItem } from "../../api/gridApi";
import { getOperativoMonthToDateRange } from "../../utils/dateRange";
import { fetchRubrosCatalogoCached } from "../../utils/rubrosCatalogCache";
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

type FiltrosRealizadosSnapshot = {
  from: string;
  to: string;
  distritoId: string;
  inspectorId: string;
  ejecucion: string;
  origen: string;
  motivoNoRealizado: string;
  realizadoTipoIniciador: string;
  realizadoRubroId: string;
  realizadoRubroLabel: string;
};

/**
 * Vista mapa DIGITALIZA: Geolocalización de domicilios (PR6C) y Realizados operativos.
 */
const MapPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const defaultRange = useMemo(() => getOperativoMonthToDateRange(), []);

  const modo = useMemo(() => parseMapaModo(searchParams.get("modo")), [searchParams]);
  const [fechaDesde, setFechaDesde] = useState(defaultRange.desde);
  const [fechaHasta, setFechaHasta] = useState(defaultRange.hasta);
  const [distritoId, setDistritoId] = useState("");

  const [ejecucion, setEjecucion] = useState("TODOS");
  const [origen, setOrigen] = useState("TODOS");
  const [motivoNoRealizado, setMotivoNoRealizado] = useState("TODAS");
  const [realizadoTipoIniciador, setRealizadoTipoIniciador] = useState("TODOS");
  const [realizadoRubroId, setRealizadoRubroId] = useState("");
  const [inspectorId, setInspectorId] = useState("");

  const [mapExpanded, setMapExpanded] = useState(false);
  const [inspectores, setInspectores] = useState<CatalogItem[]>([]);
  const [rubroOptions, setRubroOptions] = useState<{ value: string; label: string }[]>([
    { value: "", label: "Todos" },
  ]);

  const [distritoOptions, setDistritoOptions] = useState<{ value: string; label: string }[]>([
    { value: "", label: "Todos los distritos" },
  ]);

  const { features, meta, loading, error, infoMessage, loadRealizados } = useMapaOperativo();

  const filtrosUiRef = useRef<FiltrosRealizadosSnapshot>({
    from: fechaDesde,
    to: fechaHasta,
    distritoId,
    inspectorId,
    ejecucion,
    origen,
    motivoNoRealizado,
    realizadoTipoIniciador,
    realizadoRubroId,
    realizadoRubroLabel: "",
  });
  filtrosUiRef.current = {
    from: fechaDesde,
    to: fechaHasta,
    distritoId,
    inspectorId,
    ejecucion,
    origen,
    motivoNoRealizado,
    realizadoTipoIniciador,
    realizadoRubroId,
    realizadoRubroLabel:
      rubroOptions.find((o) => o.value === realizadoRubroId)?.label ?? "",
  };

  const patchFiltrosUiRef = useCallback((patch: Partial<FiltrosRealizadosSnapshot>) => {
    filtrosUiRef.current = { ...filtrosUiRef.current, ...patch };
  }, []);

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
          rubroId: s.realizadoRubroId,
          rubroLabel: s.realizadoRubroLabel,
          ejecucion: s.ejecucion,
          origen: s.origen,
          motivoNoRealizado: s.motivoNoRealizado,
        },
        opts
      );
    },
    [loadRealizados]
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
    const load = async () => {
      try {
        const items = await fetchRubrosCatalogoCached();
        setRubroOptions([
          { value: "", label: "Todos" },
          ...items.map((r) => ({ value: String(r.id), label: r.nombre })),
        ]);
      } catch {
        setRubroOptions([{ value: "", label: "Todos" }]);
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
    if (modo !== "realizados") return;
    void cargarRealizadosConSnapshotUi();
  }, [modo, fechaDesde, fechaHasta, distritoId, inspectorId, cargarRealizadosConSnapshotUi]);

  const loadRealizadosFromRef = useCallback(
    (opts?: MapaOperativoLoadOptions) => {
      void cargarRealizadosConSnapshotUi(opts);
    },
    [cargarRealizadosConSnapshotUi]
  );

  const handleAplicar = useCallback(() => {
    loadRealizadosFromRef();
  }, [loadRealizadosFromRef]);

  const handleRealizadoTipoChange = useCallback(
    (v: string) => {
      if (import.meta.env.DEV) {
        console.debug("[Mapa Realizados][tipo selected]", v);
      }
      patchFiltrosUiRef({ realizadoTipoIniciador: v });
      setRealizadoTipoIniciador(v);
      if (modo === "realizados") {
        loadRealizadosFromRef();
      }
    },
    [modo, patchFiltrosUiRef, loadRealizadosFromRef]
  );

  const handleEjecucionChange = useCallback(
    (v: string) => {
      const patch: Partial<FiltrosRealizadosSnapshot> = { ejecucion: v };
      if (v === "REALIZADO") {
        patch.motivoNoRealizado = "TODAS";
        setMotivoNoRealizado("TODAS");
      }
      if (v !== "REALIZADO") {
        patch.realizadoTipoIniciador = "TODOS";
        setRealizadoTipoIniciador("TODOS");
      }
      patchFiltrosUiRef(patch);
      setEjecucion(v);
      if (modo === "realizados") loadRealizadosFromRef();
    },
    [modo, patchFiltrosUiRef, loadRealizadosFromRef]
  );

  const handleOrigenChange = useCallback(
    (v: string) => {
      patchFiltrosUiRef({ origen: v });
      setOrigen(v);
      if (modo === "realizados") loadRealizadosFromRef();
    },
    [modo, patchFiltrosUiRef, loadRealizadosFromRef]
  );

  const handleMotivoChange = useCallback(
    (v: string) => {
      patchFiltrosUiRef({ motivoNoRealizado: v });
      setMotivoNoRealizado(v);
      if (modo === "realizados") loadRealizadosFromRef();
    },
    [modo, patchFiltrosUiRef, loadRealizadosFromRef]
  );

  const handleRealizadoRubroChange = useCallback(
    (v: string) => {
      const label = rubroOptions.find((o) => o.value === v)?.label ?? "";
      patchFiltrosUiRef({ realizadoRubroId: v, realizadoRubroLabel: label });
      setRealizadoRubroId(v);
      if (modo === "realizados") {
        loadRealizadosFromRef();
      }
    },
    [modo, patchFiltrosUiRef, loadRealizadosFromRef, rubroOptions]
  );

  const handleFechaDesdeChange = useCallback(
    (v: string) => {
      patchFiltrosUiRef({ from: v });
      setFechaDesde(v);
    },
    [patchFiltrosUiRef]
  );

  const handleFechaHastaChange = useCallback(
    (v: string) => {
      patchFiltrosUiRef({ to: v });
      setFechaHasta(v);
    },
    [patchFiltrosUiRef]
  );

  const handleDistritoIdChange = useCallback(
    (v: string) => {
      patchFiltrosUiRef({ distritoId: v });
      setDistritoId(v);
    },
    [patchFiltrosUiRef]
  );

  const handleInspectorIdChange = useCallback(
    (v: string) => {
      patchFiltrosUiRef({ inspectorId: v });
      setInspectorId(v);
    },
    [patchFiltrosUiRef]
  );

  const handleModoChange = useCallback(
    (m: MapaModo) => {
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

  const refrescarOperativoDesdeFormulario = useCallback(() => {
    queueMicrotask(() => {
      void cargarRealizadosConSnapshotUi({ forceNetwork: true });
    });
  }, [cargarRealizadosConSnapshotUi]);

  const handleLimpiarFiltros = useCallback(() => {
    const range = getOperativoMonthToDateRange();
    patchFiltrosUiRef({
      from: range.desde,
      to: range.hasta,
      distritoId: "",
      inspectorId: "",
      ejecucion: "TODOS",
      origen: "TODOS",
      motivoNoRealizado: "TODAS",
      realizadoTipoIniciador: "TODOS",
      realizadoRubroId: "",
      realizadoRubroLabel: "",
    });
    setFechaDesde(range.desde);
    setFechaHasta(range.hasta);
    setDistritoId("");
    setInspectorId("");
    setEjecucion("TODOS");
    setOrigen("TODOS");
    setMotivoNoRealizado("TODAS");
    setRealizadoTipoIniciador("TODOS");
    setRealizadoRubroId("");
    if (modo === "realizados") {
      loadRealizadosFromRef();
    }
  }, [modo, patchFiltrosUiRef, loadRealizadosFromRef]);

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
            onFechaDesdeChange={handleFechaDesdeChange}
            onFechaHastaChange={handleFechaHastaChange}
            distritoId={distritoId}
            onDistritoIdChange={handleDistritoIdChange}
            distritoOptions={distritoOptions}
            ejecucion={ejecucion}
            onEjecucionChange={handleEjecucionChange}
            origen={origen}
            onOrigenChange={handleOrigenChange}
            motivoNoRealizado={motivoNoRealizado}
            onMotivoNoRealizadoChange={handleMotivoChange}
            realizadoTipoIniciador={realizadoTipoIniciador}
            onRealizadoTipoIniciadorChange={handleRealizadoTipoChange}
            realizadoRubroId={realizadoRubroId}
            onRealizadoRubroIdChange={handleRealizadoRubroChange}
            rubroOptions={rubroOptions}
            inspectorId={inspectorId}
            onInspectorIdChange={handleInspectorIdChange}
            inspectores={inspectores}
            onAplicar={handleAplicar}
            onRefrescar={refrescarOperativoDesdeFormulario}
            onLimpiar={handleLimpiarFiltros}
          />

          <Grid
            container
            spacing={2}
            sx={{
              alignItems: "stretch",
              ...(mapExpanded
                ? { minHeight: { xs: "72vh", md: "min(92vh, 960px)" } }
                : {}),
            }}
          >
            {!mapExpanded && (
              <Grid
                size={{ xs: 12, md: 4 }}
                sx={{ order: { xs: 2, md: 1 }, display: "flex", flexDirection: "column" }}
              >
                <PanelResumenOperativo features={features} meta={meta} />
              </Grid>
            )}
            <Grid
              size={{ xs: 12, md: mapExpanded ? 12 : 8 }}
              sx={{
                order: { xs: 1, md: 2 },
                display: "flex",
                flexDirection: "column",
                alignSelf: "stretch",
                minHeight: mapExpanded ? { xs: "72vh", md: "min(92vh, 960px)" } : { xs: 420 },
              }}
            >
              <MapaCanvas
                features={features}
                loading={loading}
                mapExpanded={mapExpanded}
                fillParentHeight={!mapExpanded}
                onToggleExpand={() => setMapExpanded((e) => !e)}
                emptyMessage={infoMessage}
              />
            </Grid>
          </Grid>
        </>
      )}
    </Stack>
  );
};

export default MapPage;
