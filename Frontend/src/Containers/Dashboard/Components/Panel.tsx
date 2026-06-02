import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  FormControl,
  Grid,
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
import { alertBaseStyles, filtroItemStyles } from "../../Actuaciones/styles/filtroStyles";
import type { IndicadoresActasPorTipo } from "../../../api/indicadoresApi";
import { fetchDistritosCatalogo } from "../../../api/geolocalizacionApi";
import { fetchInspectores } from "../../../api/gridApi";
import type { Periodo } from "../../../types/periodos";
import { useIndicadoresResumen } from "../hooks/useIndicadoresResumen";
import { periodoToDateRange } from "../utils/periodoDateRange";
import ActuacionesMensualesChart from "./DashboardActuacionMensual";
import ActuacionesPorTipoChart from "./DashboardActuacionesPorTipo";
import { DashboardActasPorTipoMini, totalActasLabradas } from "./DashboardActasPorTipoChips";
import { DashboardCompactRankingCard } from "./DashboardCompactRankingCard";
import ChartCard from "./ChartCard";
import DecomisoMensualChart from "./DashboardDecomiso";
import { DashboardExecutiveKpiGrid } from "./DashboardExecutiveKpiGrid";
import KPI from "./DashboardKPI";
import RankingInspectores from "./DashboardInspectores";
import DashboardRutaItemsResumen from "./DashboardRutaItemsResumen";
import { DashboardSectionBlock } from "./DashboardSectionBlock";
import { dashboardDemoCaptionSx } from "./DashboardDemoBadge";

const ACTAS_VACIAS: IndicadoresActasPorTipo = {
  inspeccion: 0,
  notificacion: 0,
  comprobacion: 0,
  clausura: 0,
  decomiso: 0,
};

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

  const resumenParams = useMemo(() => {
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

  const { data, loading, error } = useIndicadoresResumen(resumenParams);

  const actas = data?.actas_por_tipo ?? ACTAS_VACIAS;
  const actasLabradasTotal = useMemo(() => totalActasLabradas(actas), [actas]);

  const reinspeccionesTotal = useMemo(() => {
    if (!data) return null;
    return data.reinspecciones_realizadas.notificacion + data.reinspecciones_realizadas.oficio;
  }, [data]);

  const topRubrosRanking = useMemo(
    () => (data?.top_rubros ?? []).map((r) => ({ label: r.nombre, value: r.count })),
    [data?.top_rubros],
  );

  const topContraproducenciasRanking = useMemo(
    () => (data?.contraproducencias_top ?? []).map((c) => ({ label: c.valor, value: c.count })),
    [data?.contraproducencias_top],
  );

  const tarjetasExport = data
    ? [
        { title: "Actuaciones totales", value: data.actuaciones.total },
        { title: "Actas labradas (total)", value: actasLabradasTotal },
        { title: "Kg decomisados", value: data.decomiso_kg.total_kg },
        {
          title: "Reinspecciones realizadas (total)",
          value: data.reinspecciones_realizadas.notificacion + data.reinspecciones_realizadas.oficio,
        },
        { title: "Actas inspección", value: data.actas_por_tipo.inspeccion },
        { title: "Actas notificación", value: data.actas_por_tipo.notificacion },
        { title: "Actas comprobación", value: data.actas_por_tipo.comprobacion },
        { title: "Actas clausura", value: data.actas_por_tipo.clausura },
        { title: "Actas decomiso", value: data.actas_por_tipo.decomiso },
        { title: "Mapa: pendientes cola", value: data.mapa_operativo.pendientes_cola },
        { title: "Mapa: pendientes en ruta (CT)", value: data.mapa_operativo.pendientes_completar_trabajo },
        { title: "Mapa: pendientes total", value: data.mapa_operativo.pendientes_total },
        { title: "Mapa: realizados visita", value: data.mapa_operativo.realizados_visita },
        { title: "Ítems ruta (total, fecha ruta)", value: data.ruta_items_ejecucion.total },
        {
          title: "Reinspecciones por notificación (hechas)",
          value: data.reinspecciones_realizadas.notificacion,
        },
        {
          title: "Reinspecciones por oficio (hechas)",
          value: data.reinspecciones_realizadas.oficio,
        },
      ]
    : [];

  const periodoTabIndex = PERIODOS.indexOf(periodo);
  const kpiLoading = loading && !data;

  return (
    <Box sx={functionalPageShellSx}>
      {loading ? (
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

      {error ? (
        <Alert severity="error" sx={alertBaseStyles}>
          {error}
        </Alert>
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
                data
                  ? "Exporta KPIs reales del periodo (incluye reinspecciones realizadas)."
                  : "Cargá indicadores antes de exportar."
              }
            >
              <span>
                <AppButton
                  dsVariant="primary"
                  dsSize="sm"
                  startIcon={<FileDownloadOutlinedIcon />}
                  disabled={!data || loading}
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

      {/* —— 1. Resumen ejecutivo —— */}
      <DashboardSectionBlock first title="Resumen ejecutivo">
        <DashboardExecutiveKpiGrid>
          <KPI compact title="Actuaciones totales" value={kpiLoading ? "…" : (data?.actuaciones.total ?? "—")} />
          <KPI compact title="Actas labradas" value={kpiLoading ? "…" : actasLabradasTotal} />
          <KPI compact title="Kg decomisados" value={kpiLoading ? "…" : (data?.decomiso_kg.total_kg ?? "—")} />
          <KPI
            compact
            title="Reinspecciones realizadas"
            value={kpiLoading ? "…" : (reinspeccionesTotal ?? "—")}
          />
        </DashboardExecutiveKpiGrid>
        <Box sx={{ mt: 1.25 }}>
          <DashboardActasPorTipoMini actas={actas} loading={kpiLoading} />
        </Box>
      </DashboardSectionBlock>

      {/* —— 2. Operativo / pendientes —— */}
      <DashboardSectionBlock title="Operativo / pendientes">
        <DashboardExecutiveKpiGrid
          columns={{ xs: "1fr 1fr", sm: "repeat(3, 1fr)", lg: "repeat(5, 1fr)" }}
        >
          <KPI compact title="Cola planificable" value={kpiLoading ? "…" : (data?.mapa_operativo.pendientes_cola ?? "—")} />
          <KPI
            compact
            title="En ruta (CT)"
            value={kpiLoading ? "…" : (data?.mapa_operativo.pendientes_completar_trabajo ?? "—")}
          />
          <KPI compact title="Pendientes (mapa)" value={kpiLoading ? "…" : (data?.mapa_operativo.pendientes_total ?? "—")} />
          <KPI compact title="Realizados visita" value={kpiLoading ? "…" : (data?.mapa_operativo.realizados_visita ?? "—")} />
          <KPI compact title="Ítems ruta" value={kpiLoading ? "…" : (data?.ruta_items_ejecucion.total ?? "—")} />
        </DashboardExecutiveKpiGrid>
        <Box sx={{ mt: 1.25 }}>
          <ChartCard compact title="Ítems de ruta — ejecución" loading={kpiLoading}>
            {data ? (
              <>
                <Typography variant="caption" sx={{ ...dashboardDemoCaptionSx, mt: 0, mb: 1 }}>
                  Por fecha de ruta publicada; sin filtro distrito/inspector.
                </Typography>
                <DashboardRutaItemsResumen data={data.ruta_items_ejecucion} />
              </>
            ) : (
              <Typography variant="body2" sx={{ ...dashboardDemoCaptionSx, py: 1 }}>
                {loading ? "Cargando…" : "Sin datos."}
              </Typography>
            )}
          </ChartCard>
        </Box>
      </DashboardSectionBlock>

      {/* —— 3. Riesgo bromatológico —— */}
      <DashboardSectionBlock title="Riesgo bromatológico">
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12, md: 6 }}>
            <DashboardCompactRankingCard
              title="Top rubros"
              items={topRubrosRanking}
              loading={kpiLoading}
              emptyMessage="Sin rubros con actividad en el período."
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <DashboardCompactRankingCard
              title="Top contraproducencias"
              items={topContraproducenciasRanking}
              loading={kpiLoading}
              emptyMessage="Sin contraproducencias en el período."
            />
          </Grid>
        </Grid>
      </DashboardSectionBlock>

      {/* —— 4. Productividad —— */}
      <DashboardSectionBlock title="Productividad">
        <ChartCard compact title="Ranking inspectores" loading={kpiLoading}>
          <RankingInspectores items={data?.ranking_inspectores ?? []} />
        </ChartCard>
      </DashboardSectionBlock>

      {/* —— 5. Tendencias —— */}
      <DashboardSectionBlock title="Tendencias">
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12, lg: 8 }}>
            <ChartCard compact title="Actas labradas — tendencia mensual" loading={kpiLoading}>
              <ActuacionesMensualesChart items={data?.actas_labradas_mensual ?? []} loading={loading} />
            </ChartCard>
          </Grid>
          <Grid size={{ xs: 12, lg: 4 }}>
            <ChartCard compact title="Kg decomisados" loading={kpiLoading}>
              <DecomisoMensualChart decomisoKg={data?.decomiso_kg ?? null} loading={loading} />
            </ChartCard>
          </Grid>
        </Grid>
      </DashboardSectionBlock>

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
          <ActuacionesPorTipoChart items={data?.actuaciones_por_tipo_operativo ?? []} />
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};

export default Panel;
