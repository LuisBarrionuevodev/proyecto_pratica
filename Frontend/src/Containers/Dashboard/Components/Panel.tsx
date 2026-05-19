import {
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
import ChartCard from "./ChartCard";
import ContraproducenciaPorTipoChart from "./DashboardContraproducenciaPorTipo";
import DashboardContraproducenciasTop from "./DashboardContraproducenciasTop";
import DecomisoMensualChart from "./DashboardDecomiso";
import DistribucionTipoChart from "./DashboardDistribucion";
import EfectivasInefectivasChart from "./DashboardFunnel";
import KPI from "./DashboardKPI";
import RankingInspectores from "./DashboardInspectores";
import DashboardRutaItemsResumen from "./DashboardRutaItemsResumen";
import ReinspeccionesRealizadasChart from "./DashboardReinspecciones";
import TopRubrosChart from "./DashboardTopRubros";
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
  const actu = data?.actuaciones;

  const tarjetasExport = data
    ? [
        { title: "Actuaciones totales", value: data.actuaciones.total },
        { title: "Con contraproducencia", value: data.actuaciones.con_contraproducencia },
        { title: "Sin contraproducencia", value: data.actuaciones.sin_contraproducencia },
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
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 2,
          }}
        >
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

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI title="Actuaciones" value={loading && !data ? "…" : (actu?.total ?? "—")} periodo={periodo} icon={null} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI
            title="Con contraproducencia"
            value={loading && !data ? "…" : (actu?.con_contraproducencia ?? "—")}
            periodo={periodo}
            icon={null}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI
            title="Sin contraproducencia"
            value={loading && !data ? "…" : (actu?.sin_contraproducencia ?? "—")}
            periodo={periodo}
            icon={null}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI
            title="Pendientes (mapa)"
            value={loading && !data ? "…" : (data?.mapa_operativo.pendientes_total ?? "—")}
            periodo={periodo}
            icon={null}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI
            title="Cola planificable"
            value={loading && !data ? "…" : (data?.mapa_operativo.pendientes_cola ?? "—")}
            periodo={periodo}
            icon={null}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI
            title="En ruta (completar trabajo)"
            value={loading && !data ? "…" : (data?.mapa_operativo.pendientes_completar_trabajo ?? "—")}
            periodo={periodo}
            icon={null}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI
            title="Realizados visita (mapa)"
            value={loading && !data ? "…" : (data?.mapa_operativo.realizados_visita ?? "—")}
            periodo={periodo}
            icon={null}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI
            title="Ítems ruta (global)"
            value={loading && !data ? "…" : (data?.ruta_items_ejecucion.total ?? "—")}
            periodo={periodo}
            icon={null}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 8 }}>
          <ChartCard title={`Actas labradas — tendencia (${desde} → ${hasta})`} loading={loading && !data}>
            <ActuacionesMensualesChart
              items={data?.actas_labradas_mensual ?? []}
              loading={loading}
            />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <ChartCard title={`Kilos decomisados (${desde} → ${hasta})`} loading={loading && !data}>
            <DecomisoMensualChart decomisoKg={data?.decomiso_kg ?? null} loading={loading} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 7 }}>
          <ChartCard title={`Top contraproducencias (${desde} → ${hasta})`} loading={loading && !data}>
            <DashboardContraproducenciasTop items={data?.contraproducencias_top ?? []} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <ChartCard title={`Actas por tipo (${desde} → ${hasta})`} loading={loading && !data}>
            <DistribucionTipoChart actas={actas} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6, lg: 4 }}>
          <ChartCard title={`Top rubros (${desde} → ${hasta})`} loading={loading && !data}>
            <TopRubrosChart items={data?.top_rubros ?? []} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12 }}>
          <ChartCard
            title="Ítems de ruta — ejecución"
            loading={loading && !data}
          >
            {data ? (
              <>
                <Typography variant="caption" sx={{ ...dashboardDemoCaptionSx, mt: 0, mb: 1.5 }}>
                  Por fecha de ruta publicada; sin filtro distrito/inspector. ≠ realizados del mapa.
                </Typography>
                <DashboardRutaItemsResumen data={data.ruta_items_ejecucion} />
              </>
            ) : (
              <Typography variant="body2" sx={{ ...dashboardDemoCaptionSx, py: 2 }}>
                {loading ? "Cargando…" : "Sin datos."}
              </Typography>
            )}
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 8 }}>
          <ChartCard title={`Ranking inspectores (${desde} → ${hasta})`} loading={loading && !data}>
            <RankingInspectores items={data?.ranking_inspectores ?? []} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6, lg: 4 }}>
          <ChartCard title={`Tipo de contraproducencia (${desde} → ${hasta})`} loading={loading && !data}>
            <ContraproducenciaPorTipoChart items={data?.contraproducencias_por_tipo ?? []} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6, lg: 4 }}>
          <ChartCard title={`Tipo de actuación (${desde} → ${hasta})`} loading={loading && !data}>
            <ActuacionesPorTipoChart items={data?.actuaciones_por_tipo_operativo ?? []} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, md: 6, lg: 4 }}>
          <ChartCard title={`Reinspecciones realizadas (${desde} → ${hasta})`} loading={loading && !data}>
            <ReinspeccionesRealizadasChart data={data?.reinspecciones_realizadas ?? null} />
            <Typography component="span" sx={dashboardDemoCaptionSx}>
              Fecha de cierre de ruta (visita realizada con actuación vinculada).
            </Typography>
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <ChartCard title={`Actuaciones sin / con contraproducencia (${desde} → ${hasta})`} loading={loading && !data}>
            <EfectivasInefectivasChart
              sinContraproducencia={actu?.sin_contraproducencia ?? 0}
              conContraproducencia={actu?.con_contraproducencia ?? 0}
            />
          </ChartCard>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Panel;
