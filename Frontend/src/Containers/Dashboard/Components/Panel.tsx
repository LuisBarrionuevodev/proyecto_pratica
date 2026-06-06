import {
  Box,
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
import {
  GLASS_COLORS,
  moduleFiltersSurfaceSx,
  moduleSlicesPanelPaperSx,
  moduleSlicesTabsSx,
} from "../../../styles/GlassStyles";
import { dashboardAnalyticsCardSx } from "../../../styles/DashboardStyles";
import { AppButton } from "../../../ui";
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
import { DashboardActasPorTipoSection } from "./DashboardActasPorTipoSection";
import { DashboardEjecutivoSection } from "./DashboardEjecutivoSection";
import { DashboardPendientesSection } from "./DashboardPendientesSection";
import { DashboardNoRealizadasSection } from "./DashboardNoRealizadasSection";
import { DashboardProductividadSection } from "./DashboardProductividadSection";
import { DashboardRiesgoSection } from "./DashboardRiesgoSection";

const PERIODOS: Periodo[] = ["Semanal", "Mensual", "Trimestral", "Anual"];

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
        { title: "Relevamientos pendientes", value: p.relevamientos_pendientes },
        { title: "Reinspecciones oficio pendientes", value: p.reinspecciones_oficio_pendientes },
        {
          title: "Reinspecciones notificación pendientes",
          value: p.reinspecciones_notificacion_pendientes,
        },
        { title: "Denuncias pendientes", value: p.denuncias_pendientes },
        { title: "Pendientes sin geolocalización", value: p.pendientes_geolocalizacion },
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
  const anyLoading =
    (ejecutivoLoading && !ejecutivoData) ||
    (pendientesLoading && !pendientesData) ||
    (riesgoLoading && !riesgoData) ||
    (noRealizadasLoading && !noRealizadasData) ||
    (productividadLoading && !productividadData);

  return (
    <Box sx={functionalPageShellSx}>
      {anyLoading ? (
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
          ...dashboardAnalyticsCardSx,
          ...moduleSlicesPanelPaperSx,
          p: 0,
          overflow: "hidden",
        }}
      >
        <Tabs
          value={periodoTabIndex}
          onChange={(_, v) => setPeriodo(PERIODOS[v] ?? "Mensual")}
          variant="scrollable"
          allowScrollButtonsMobile
          sx={{
            ...moduleSlicesTabsSx,
            minHeight: 42,
            borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
          }}
        >
          {PERIODOS.map((p) => (
            <Tab key={p} label={p} sx={{ minHeight: 42, py: 0.75 }} />
          ))}
        </Tabs>
        <Box
          sx={{
            ...moduleFiltersSurfaceSx,
            border: "none",
            borderRadius: 0,
            boxShadow: "none",
            backgroundColor: "transparent",
            p: { xs: 1.25, sm: 1.5 },
            display: "flex",
            flexDirection: { xs: "column", md: "row" },
            flexWrap: "wrap",
            gap: 1.25,
            alignItems: { xs: "stretch", md: "flex-end" },
          }}
        >
          <FormControl
            variant="outlined"
            sx={[filtroItemStyles, { minWidth: { xs: "100%", sm: 200 }, flex: { md: "1 1 180px" } }]}
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
            sx={[filtroItemStyles, { minWidth: { xs: "100%", sm: 200 }, flex: { md: "1 1 180px" } }]}
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
              <AppButton
                dsVariant="primary"
                dsSize="sm"
                startIcon={<FileDownloadOutlinedIcon />}
                disabled={tarjetasExport.length === 0 || anyLoading}
                onClick={() =>
                  exportDashboardToExcel({
                    tarjetas: tarjetasExport,
                    periodoLabel: `${periodo} (${desde} → ${hasta})`,
                  })
                }
                sx={{ alignSelf: { xs: "stretch", md: "center" }, whiteSpace: "nowrap" }}
              >
                Exportar KPIs
              </AppButton>
            </span>
          </Tooltip>
        </Box>
      </Paper>

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
    </Box>
  );
};

export default Panel;
