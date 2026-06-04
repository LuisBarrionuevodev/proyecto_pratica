import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
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
import { dashboardGlassCardSx } from "../../../styles/DashboardStyles";
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
import { useIndicadoresResumen } from "../hooks/useIndicadoresResumen";
import { periodoToDateRange } from "../utils/periodoDateRange";
import ActuacionesPorTipoChart from "./DashboardActuacionesPorTipo";
import { DashboardEjecutivoSection } from "./DashboardEjecutivoSection";
import { DashboardPendientesSection } from "./DashboardPendientesSection";
import { DashboardNoRealizadasSection } from "./DashboardNoRealizadasSection";
import { DashboardProductividadSection } from "./DashboardProductividadSection";
import { DashboardRiesgoSection } from "./DashboardRiesgoSection";
import { DashboardTendenciasSection } from "./DashboardTendenciasSection";
import { DashboardSectionBlock } from "./DashboardSectionBlock";

const PERIODOS: Periodo[] = ["Semanal", "Mensual", "Trimestral", "Anual"];

const Panel = () => {
  const [periodo, setPeriodo] = useState<Periodo>("Mensual");
  const initialRange = useMemo(() => periodoToDateRange("Mensual"), []);
  const [desde, setDesde] = useState(initialRange.desde);
  const [hasta, setHasta] = useState(initialRange.hasta);
  const [distritoId, setDistritoId] = useState<string>("");
  const [inspectorId, setInspectorId] = useState<string>("");
  const [distritoOptions, setDistritoOptions] = useState<{ id: number; nombre: string }[]>([]);
  const [inspectorOptions, setInspectorOptions] = useState<{ id: number; nombre: string }[]>([]);

  useEffect(() => {
    const r = periodoToDateRange(periodo);
    setDesde(r.desde);
    setHasta(r.hasta);
  }, [periodo]);

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
    if (!desde || !hasta) return null;
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

  const {
    data: resumenData,
    loading: resumenLoading,
    error: resumenError,
  } = useIndicadoresResumen(indicadoresParams);

  const tarjetasExport = useMemo(() => {
    const cards: { title: string; value: number | string }[] = [];
    if (ejecutivoData) {
      const k = ejecutivoData.kpis;
      const a = ejecutivoData.actas_por_tipo;
      cards.push(
        { title: "Actuaciones realizadas", value: k.actuaciones_realizadas },
        { title: "Actas labradas (total)", value: k.actas_labradas },
        { title: "Kg decomisados", value: k.mercaderia_decomisada_kg },
        {
          title: "Reinspecciones por notificación (hechas)",
          value: k.reinspecciones_notificacion_realizadas,
        },
        {
          title: "Ratificaciones de clausura (hechas)",
          value: k.ratificaciones_clausura_realizadas,
        },
        {
          title: "Ratificaciones de decomiso (hechas)",
          value: k.ratificaciones_decomiso_realizadas,
        },
        { title: "Verificar e informar (hechas)", value: k.verificar_informar_realizadas },
        { title: "Actas inspección", value: a.inspeccion },
        { title: "Actas notificación", value: a.notificacion },
        { title: "Actas comprobación", value: a.comprobacion },
        { title: "Actas clausura", value: a.clausura },
        { title: "Actas decomiso", value: a.decomiso }
      );
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
        { title: "Pendientes sin geolocalización", value: p.pendientes_geolocalizacion }
      );
    }
    if (noRealizadasData) {
      const pt = noRealizadasData.por_tipo;
      const total =
        pt.inspeccion +
        pt.reinspeccion_oficio +
        pt.reinspeccion_notificacion +
        pt.denuncia;
      const topCp = noRealizadasData.top_contraproducencias[0];
      const topDist = noRealizadasData.distritos_con_mas_no_realizadas[0];
      cards.push(
        { title: "Total no realizadas", value: total },
        { title: "No realizadas inspección", value: pt.inspeccion },
        { title: "No realizadas reins. oficio", value: pt.reinspeccion_oficio },
        {
          title: "No realizadas reins. notificación",
          value: pt.reinspeccion_notificacion,
        },
        { title: "No realizadas denuncia", value: pt.denuncia }
      );
      if (topCp) {
        cards.push({
          title: "Principal contraproducencia (no realizadas)",
          value: `${topCp.contraproducencia} (${topCp.cantidad})`,
        });
      }
      if (topDist) {
        cards.push({
          title: "Distrito con más no realizadas",
          value: `${topDist.distrito_nombre} (${topDist.cantidad})`,
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
    if (riesgoData) {
      const r = riesgoData.top_rubros[0];
      const mn = riesgoData.top_motivos_notificacion[0];
      const mc = riesgoData.top_motivos_comprobacion[0];
      const dk = riesgoData.decomiso_kg_por_rubro;
      const totalKgRubro = dk.reduce((sum, row) => sum + row.kg, 0);
      const topKgRubro = dk[0];
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
      if (totalKgRubro > 0) {
        cards.push({ title: "Riesgo: kg decomisados (total por rubro)", value: totalKgRubro });
      }
      if (topKgRubro) {
        cards.push({
          title: "Riesgo: rubro con más kg decomisados",
          value: `${topKgRubro.rubro} (${topKgRubro.kg} kg)`,
        });
      }
    }
    return cards;
  }, [ejecutivoData, pendientesData, riesgoData, noRealizadasData, productividadData]);

  const periodoTabIndex = PERIODOS.indexOf(periodo);
  const tendenciasLoading = resumenLoading && !resumenData;
  const anyLoading =
    tendenciasLoading ||
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

      <Paper elevation={0} sx={moduleSlicesPanelPaperSx}>
        <Tabs
          value={periodoTabIndex}
          onChange={(_, v) => setPeriodo(PERIODOS[v] ?? "Mensual")}
          variant="scrollable"
          allowScrollButtonsMobile
          sx={moduleSlicesTabsSx}
        >
          {PERIODOS.map((p) => (
            <Tab key={p} label={p} />
          ))}
        </Tabs>
      </Paper>

      <Paper elevation={0} sx={moduleFiltersSurfaceSx}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Typography
            variant="body2"
            sx={{
              fontFamily: '"Tactic Sans", sans-serif',
              color: GLASS_COLORS.textSecondary,
              fontSize: "0.8125rem",
            }}
          >
            Indicadores según el período y filtros seleccionados (datos reales del servidor).
          </Typography>

          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", lg: "row" },
              flexWrap: "wrap",
              gap: 2,
              alignItems: { xs: "stretch", lg: "flex-end" },
            }}
          >
            <TextField
              type="date"
              label="Desde"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              variant="outlined"
              sx={filtroItemStyles}
            />
            <TextField
              type="date"
              label="Hasta"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              variant="outlined"
              sx={filtroItemStyles}
            />
            <FormControl variant="outlined" sx={[filtroItemStyles, { minWidth: { xs: "100%", sm: 200 } }]}>
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
            <FormControl variant="outlined" sx={[filtroItemStyles, { minWidth: { xs: "100%", sm: 200 } }]}>
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
                  ? "Exporta KPIs visibles del periodo (ejecutivo, pendientes, riesgo, no realizadas y productividad)."
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
                      periodoLabel: `${desde} → ${hasta}`,
                    })
                  }
                  sx={{ alignSelf: { xs: "stretch", lg: "center" }, whiteSpace: "nowrap" }}
                >
                  Exportar KPIs
                </AppButton>
              </span>
            </Tooltip>
          </Box>
        </Box>
      </Paper>

      <DashboardEjecutivoSection
        data={ejecutivoData}
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

      <DashboardTendenciasSection
        data={resumenData}
        loading={resumenLoading}
        error={resumenError}
      />

      {/* Detalle secundario: tipo operativo (colapsable) */}
      <Accordion
        disableGutters
        elevation={0}
        sx={{
          mt: 1.5,
          ...dashboardGlassCardSx,
          "&:before": { display: "none" },
          borderRadius: "12px !important",
          overflow: "hidden",
        }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon sx={{ color: GLASS_COLORS.textPrimary }} />}
          sx={{
            minHeight: 48,
            "& .MuiAccordionSummary-content": { my: 1 },
          }}
        >
          <Typography
            sx={{
              fontFamily: '"Tactic Sans", sans-serif',
              fontWeight: 600,
              fontSize: "0.9375rem",
              color: GLASS_COLORS.textPrimary,
            }}
          >
            Detalle: actuaciones por tipo operativo
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ pt: 0, pb: 2, px: 2 }}>
          <ActuacionesPorTipoChart items={resumenData?.actuaciones_por_tipo_operativo ?? []} />
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};

export default Panel;
