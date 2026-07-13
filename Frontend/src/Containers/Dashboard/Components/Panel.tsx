import {
  Box,
  Button,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Tab,
  Tabs,
  Tooltip,
} from "@mui/material";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import { useEffect, useMemo, useState } from "react";

import { exportDashboardToExcel } from "../../../utils/exportExcelDashboard";
import { functionalPageShellSx } from "../../../styles/functionalPageShell";
import { moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../../styles/GlassStyles";
import { dashboardPeriodTabsSx } from "../../../styles/DashboardStyles";
import { TableExportBoxStyles, TableExportButtonStyles } from "../../../styles/TablasStyle";
import { filtroItemStyles } from "../../Actuaciones/styles/filtroStyles";
import { fetchDistritosCatalogo } from "../../../api/geolocalizacionApi";
import { fetchInspectores } from "../../../api/gridApi";
import type { Periodo } from "../../../types/periodos";
import { useIndicadoresEjecutivo } from "../hooks/useIndicadoresEjecutivo";
import { useIndicadoresPendientes } from "../hooks/useIndicadoresPendientes";
import { useIndicadoresNoRealizadas } from "../hooks/useIndicadoresNoRealizadas";
import { useIndicadoresProductividad } from "../hooks/useIndicadoresProductividad";
import { useIndicadoresRiesgo } from "../hooks/useIndicadoresRiesgo";
import { periodoToDateRange } from "../utils/periodoDateRange";
import { DashboardIndicadoresPageLoader } from "./DashboardIndicadoresPageLoader";
import { DashboardEjecutivoSection } from "./DashboardEjecutivoSection";
import { DashboardPendientesSection } from "./DashboardPendientesSection";
import { DashboardNoRealizadasSection } from "./DashboardNoRealizadasSection";
import { DashboardProductividadSection } from "./DashboardProductividadSection";
import { DashboardRiesgoSection } from "./DashboardRiesgoSection";

const PERIODOS: Periodo[] = ["Semanal", "Mensual", "Trimestral", "Anual"];

/**
 * Pendiente D1d.12 — Tribunal de falta (no implementar en este PR):
 * cohorte por inicio de trámite, comprobaciones/multas en rango, respuestas del tribunal
 * (ratificación decomiso, verificar e informar, ratificación clausura, etc.) y ejecución exitosa.
 * Requiere relevamiento y endpoints propios.
 */

const Panel = () => {
  const [periodo, setPeriodo] = useState<Periodo>("Mensual");
  const [distritoId, setDistritoId] = useState<string>("");
  const [inspectorId, setInspectorId] = useState<string>("");
  const [distritoOptions, setDistritoOptions] = useState<{ id: number; nombre: string }[]>([]);
  const [inspectorOptions, setInspectorOptions] = useState<{ id: number; nombre: string }[]>([]);

  const { desde, hasta } = useMemo(() => periodoToDateRange(periodo), [periodo]);

  useEffect(() => {
    let cancel = false;
    fetchDistritosCatalogo()
      .then((res) => {
        if (!cancel) setDistritoOptions(res.items.map((i) => ({ id: i.id, nombre: i.nombre })));
      })
      .catch(() => {
        if (!cancel) setDistritoOptions([]);
      });
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    let cancel = false;
    fetchInspectores()
      .then((res) => {
        if (!cancel) setInspectorOptions(res.items.map((i) => ({ id: i.id, nombre: i.nombre })));
      })
      .catch(() => {
        if (!cancel) setInspectorOptions([]);
      });
    return () => {
      cancel = true;
    };
  }, []);

  const indicadoresParams = useMemo(() => {
    const p: {
      desde: string;
      hasta: string;
      distrito_id?: number;
      inspector_id?: number;
    } = { desde, hasta };
    if (distritoId !== "") {
      p.distrito_id = Number(distritoId);
    }
    if (inspectorId !== "") {
      p.inspector_id = Number(inspectorId);
    }
    return p;
  }, [desde, hasta, distritoId, inspectorId]);

  const {
    data: ejecutivoData,
    loading: ejecutivoLoading,
    error: ejecutivoError,
  } = useIndicadoresEjecutivo(indicadoresParams);

  const {
    data: pendientesData,
    loading: pendientesLoading,
    error: pendientesError,
  } = useIndicadoresPendientes(indicadoresParams);

  const {
    data: riesgoData,
    loading: riesgoLoading,
    error: riesgoError,
  } = useIndicadoresRiesgo(indicadoresParams);

  const {
    data: noRealizadasData,
    loading: noRealizadasLoading,
    error: noRealizadasError,
  } = useIndicadoresNoRealizadas(indicadoresParams);

  const {
    data: productividadData,
    loading: productividadLoading,
    error: productividadError,
  } = useIndicadoresProductividad(indicadoresParams);

  const noRealizadasTotal = useMemo(() => {
    if (!noRealizadasData) return null;
    const pt = noRealizadasData.por_tipo;
    return pt.inspeccion + pt.reinspeccion_oficio + pt.reinspeccion_notificacion + pt.denuncia;
  }, [noRealizadasData]);

  const tarjetasExport = useMemo(() => {
    const cards: { title: string; value: number | string }[] = [];
    if (ejecutivoData) {
      const k = ejecutivoData.kpis;
      const a = ejecutivoData.actas_por_tipo;
      cards.push(
        { title: "Actuaciones realizadas", value: k.actuaciones_realizadas },
        { title: "Actas labradas (total)", value: k.actas_labradas },
        {
          title: "Reinspecciones por notificación (realizadas)",
          value: k.reinspecciones_notificacion_realizadas,
        },
        { title: "Mercadería decomisada (kg)", value: k.mercaderia_decomisada_kg },
        {
          title: "Ratificaciones de clausura (realizadas)",
          value: k.ratificaciones_clausura_realizadas,
        },
        {
          title: "Ratificaciones de decomiso (realizadas)",
          value: k.ratificaciones_decomiso_realizadas,
        },
        { title: "Verificar e informar (realizadas)", value: k.verificar_informar_realizadas },
        { title: "Actas inspección", value: a.inspeccion },
        { title: "Actas notificación", value: a.notificacion },
        { title: "Actas comprobación", value: a.comprobacion },
        { title: "Actas clausura", value: a.clausura },
        { title: "Actas decomiso", value: a.decomiso },
      );
    }
    if (noRealizadasTotal != null) {
      cards.push({ title: "Total no realizadas", value: noRealizadasTotal });
    }
    if (pendientesData) {
      const p = pendientesData.kpis;
      cards.push(
        { title: "Reinspecciones oficio pendientes", value: p.reinspecciones_oficio_pendientes },
        {
          title: "Reinspecciones notificación pendientes",
          value: p.reinspecciones_notificacion_pendientes,
        },
        { title: "Denuncias pendientes", value: p.denuncias_pendientes },
      );
    }
    if (riesgoData) {
      const r = riesgoData.top_rubros[0];
      const mn = riesgoData.top_motivos_notificacion[0];
      const mc = riesgoData.top_motivos_comprobacion[0];
      if (r) {
        cards.push({ title: "Riesgo: top rubro", value: `${r.rubro} (${r.cantidad})` });
      }
      if (mn) {
        cards.push({
          title: "Riesgo: top motivo notificación",
          value: `${mn.motivo} (${mn.cantidad})`,
        });
      }
      if (mc) {
        cards.push({
          title: "Riesgo: top motivo comprobación",
          value: `${mc.motivo} (${mc.cantidad})`,
        });
      }
      if (ejecutivoData) {
        cards.push({
          title: "Riesgo: mercadería decomisada total (kg)",
          value: ejecutivoData.kpis.mercaderia_decomisada_kg,
        });
      }
    }
    if (productividadData) {
      const topReal = productividadData.inspectores_realizadas[0];
      const topNoReal = productividadData.inspectores_no_realizadas[0];
      const topActas = productividadData.actas_por_inspector[0];
      if (topReal) {
        cards.push({
          title: "Top inspector por actuaciones realizadas",
          value: `${topReal.inspector} (${topReal.total_realizadas})`,
        });
      }
      if (topNoReal) {
        cards.push({
          title: "Top inspector por no realizadas",
          value: `${topNoReal.inspector} (${topNoReal.total_no_realizadas})`,
        });
      }
      if (topActas) {
        cards.push({
          title: "Top inspector por actas labradas",
          value: `${topActas.inspector} (${topActas.total_actas})`,
        });
      }
    }
    return cards;
  }, [ejecutivoData, pendientesData, riesgoData, noRealizadasTotal, productividadData]);

  const periodoTabIndex = PERIODOS.indexOf(periodo);
  const isInitialLoading =
    (ejecutivoLoading && !ejecutivoData && !ejecutivoError) ||
    (pendientesLoading && !pendientesData && !pendientesError) ||
    (riesgoLoading && !riesgoData && !riesgoError) ||
    (noRealizadasLoading && !noRealizadasData && !noRealizadasError) ||
    (productividadLoading && !productividadData && !productividadError);

  const isRefreshing =
    !isInitialLoading &&
    (ejecutivoLoading ||
      pendientesLoading ||
      riesgoLoading ||
      noRealizadasLoading ||
      productividadLoading);

  const anyBlockingLoad = isInitialLoading || isRefreshing;

  return (
    <Box sx={functionalPageShellSx}>
      {isRefreshing ? (
        <LinearProgress
          sx={{
            position: "sticky",
            top: 0,
            zIndex: 2,
            borderRadius: 1,
            mb: -1,
          }}
        />
      ) : null}

      <Paper
        elevation={0}
        sx={{
          ...moduleSlicesPanelPaperSx,
          flexDirection: { xs: "column", md: "row" },
          alignItems: { xs: "stretch", md: "center" },
          gap: { xs: 1.25, md: 1.5 },
          px: { xs: 0.5, sm: 1 },
          overflow: "visible",
        }}
      >
          <Tabs
            value={periodoTabIndex}
            onChange={(_, v) => setPeriodo(PERIODOS[v] ?? "Mensual")}
            variant="scrollable"
            allowScrollButtonsMobile
            sx={{
              ...moduleSlicesTabsSx,
              ...dashboardPeriodTabsSx,
              flex: 1,
              minWidth: 0,
              alignSelf: { md: "stretch" },
            }}
          >
            {PERIODOS.map((p) => (
              <Tab key={p} label={p} />
            ))}
          </Tabs>

          <Box
            sx={{
              ...TableExportBoxStyles,
              p: 0,
              flexDirection: { xs: "column", sm: "row" },
              flexWrap: "wrap",
              alignItems: { xs: "stretch", sm: "center" },
              justifyContent: { sm: "flex-end" },
              flexShrink: 0,
              gap: 1.25,
              width: { xs: "100%", md: "auto" },
            }}
          >
          <FormControl
            variant="outlined"
            sx={[filtroItemStyles, { minWidth: { xs: "100%", sm: 168 }, flex: { sm: "0 1 168px" } }]}
          >
            <InputLabel id="dash-distrito-label" shrink>
              Distrito
            </InputLabel>
            <Select
              labelId="dash-distrito-label"
              label="Distrito"
              notched
              displayEmpty
              value={distritoId}
              onChange={(e) => setDistritoId(String(e.target.value))}
            >
              <MenuItem value="">
                <em>Todos</em>
              </MenuItem>
              {distritoOptions.map((d) => (
                <MenuItem key={d.id} value={String(d.id)}>
                  {d.nombre}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl
            variant="outlined"
            sx={[filtroItemStyles, { minWidth: { xs: "100%", sm: 168 }, flex: { sm: "0 1 168px" } }]}
          >
            <InputLabel id="dash-inspector-label" shrink>
              Inspector
            </InputLabel>
            <Select
              labelId="dash-inspector-label"
              label="Inspector"
              notched
              displayEmpty
              value={inspectorId}
              onChange={(e) => setInspectorId(String(e.target.value))}
            >
              <MenuItem value="">
                <em>Todos</em>
              </MenuItem>
              {inspectorOptions.map((i) => (
                <MenuItem key={i.id} value={String(i.id)}>
                  {i.nombre}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Tooltip
            title={
              tarjetasExport.length > 0
                ? "Exporta KPIs visibles del período seleccionado."
                : "Cargá indicadores antes de exportar."
            }
          >
            <span>
              <Button
                startIcon={<FileDownloadOutlinedIcon />}
                disabled={tarjetasExport.length === 0 || anyBlockingLoad}
                onClick={() =>
                  exportDashboardToExcel({
                    tarjetas: tarjetasExport,
                    periodoLabel: `${periodo} (${desde} → ${hasta})`,
                  })
                }
                sx={{
                  ...TableExportButtonStyles,
                  fontWeight: 700,
                  alignSelf: { xs: "stretch", sm: "center" },
                  whiteSpace: "nowrap",
                }}
              >
                Exportar KPIs
              </Button>
            </span>
          </Tooltip>
          </Box>
      </Paper>

      {isInitialLoading ? (
        <DashboardIndicadoresPageLoader />
      ) : (
        <>
          <DashboardEjecutivoSection
            data={ejecutivoData}
            noRealizadasTotal={noRealizadasTotal}
            loading={ejecutivoLoading}
            error={ejecutivoError}
          />

          <DashboardActasPorTipoSection
            actas={ejecutivoData?.actas_por_tipo}
            loading={ejecutivoLoading}
            error={ejecutivoError}
          />

          <DashboardPendientesSection
            data={pendientesData}
            loading={pendientesLoading}
            error={pendientesError}
          />

          <DashboardRiesgoSection
            data={riesgoData}
            mercaderiaDecomisadaKg={ejecutivoData?.kpis.mercaderia_decomisada_kg}
            loading={riesgoLoading}
            error={riesgoError}
          />

          <DashboardNoRealizadasSection
            data={noRealizadasData}
            loading={noRealizadasLoading}
            error={noRealizadasError}
          />

          <DashboardProductividadSection
            data={productividadData}
            loading={productividadLoading}
            error={productividadError}
          />
        </>
      )}
    </Box>
  );
};

export default Panel;
