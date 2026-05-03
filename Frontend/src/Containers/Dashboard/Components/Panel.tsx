import { Alert, Box, Button, CircularProgress, FormControl, Grid, InputLabel, MenuItem, Select, TextField, Typography } from "@mui/material";
import { exportDashboardToExcel } from "../../../utils/exportExcelDashboard";
import ActuacionesMensualesChart from "./DashboardActuacionMensual";
import DecomisoMensualChart from "./DashboardDecomiso";
import { type Inspector } from "./DashboardInspectores";
import DistribucionTipoChart from "./DashboardDistribucion";
import ComparacionTurnoChart from "./DashboardTurnos";
import PipelineChart from "./DashboardEmbudo";
import ChartCard from "./ChartCard";
import EfectivasInefectivasChart from "./DashboardFunnel";
import KPI from "./DashboardKPI";
import DashboardContraproducenciasTop from "./DashboardContraproducenciasTop";
import DashboardRutaItemsResumen from "./DashboardRutaItemsResumen";
import TopRubrosChart from "./DashboardTopRubros";
import { filtroItemStyles } from "../../Actuaciones/styles/filtroStyles";
import { useEffect, useMemo, useState } from "react";
import type { Periodo } from "../../../types/periodos";
import RankingInspectores from "./DashboardInspectores";
import { periodoToDateRange } from "../utils/periodoDateRange";
import { useIndicadoresResumen } from "../hooks/useIndicadoresResumen";
import { fetchDistritosCatalogo } from "../../../api/geolocalizacionApi";
import { fetchInspectores } from "../../../api/gridApi";
import type { IndicadoresActasPorTipo } from "../../../api/indicadoresApi";

const ACTAS_VACIAS: IndicadoresActasPorTipo = {
  inspeccion: 0,
  notificacion: 0,
  comprobacion: 0,
  clausura: 0,
  decomiso: 0,
};

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

  const inspectores: Inspector[] = [
    { id: 1, nombre: "Gómez", inspecciones: 124 },
    { id: 2, nombre: "Luna", inspecciones: 98 },
    { id: 3, nombre: "Pérez", inspecciones: 156 },
    { id: 4, nombre: "Sosa", inspecciones: 87 },
    { id: 5, nombre: "Díaz", inspecciones: 142 },
    { id: 6, nombre: "Romero", inspecciones: 110 },
    { id: 7, nombre: "Torres", inspecciones: 76 },
    { id: 8, nombre: "Rojas", inspecciones: 133 },
    { id: 9, nombre: "Fernández", inspecciones: 123 },
    { id: 10, nombre: "Gutiérrez", inspecciones: 52 },
    { id: 11, nombre: "Martínez", inspecciones: 23 },
    { id: 12, nombre: "Acosta", inspecciones: 41 },
    { id: 13, nombre: "Benítez", inspecciones: 53 },
    { id: 14, nombre: "Herrera", inspecciones: 26 },
    { id: 15, nombre: "Silva", inspecciones: 22 },
    { id: 16, nombre: "Molina", inspecciones: 11 },
    { id: 17, nombre: "Castro", inspecciones: 64 },
    { id: 18, nombre: "Vera", inspecciones: 22 },
    { id: 19, nombre: "Navarro", inspecciones: 43 },
    { id: 20, nombre: "Ibarra", inspecciones: 57 },
  ];

  const lineChartData = [
    { mes: "Ene", actu: 40 },
    { mes: "Feb", actu: 55 },
    { mes: "Mar", actu: 90 },
    { mes: "Abr", actu: 75 },
    { mes: "May", actu: 120 },
  ];

  const pieChartData = [
    { rubro: "Panaderia", clausuras: 120 },
    { rubro: "Carniceria", clausuras: 90 },
    { rubro: "Drugstore", clausuras: 70 },
    { rubro: "Kiosco", clausuras: 50 },
    { rubro: "Fiambreria", clausuras: 40 },
    { rubro: "Otros", clausuras: 30 },
  ];

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
      ]
    : [{ title: "Sin datos cargados", value: 0 }];

  return (
    <Box p={3} ml={3}>
      {loading && (
        <Box sx={{ mb: 2 }}>
          <CircularProgress size={28} sx={{ color: "#0166FF" }} />
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box display={"flex"} flexDirection={{ xs: "column", md: "column", lg: "row" }} justifyContent={"space-between"} alignItems={"center"}>
        <Typography variant="body2" sx={{ color: "rgba(255, 255, 255, 0.65)", maxWidth: { xs: "100%", lg: 280 } }}>
          Indicadores según el período y filtros seleccionados (datos reales del servidor).
        </Typography>
        <Box
          display="flex"
          flexDirection={{ xs: "column", md: "row" }}
          bgcolor="#2B2E34"
          borderRadius={3}
          height={{ xs: "auto", md: "50px" }}
        >
          {(["Semanal", "Mensual", "Trimestral", "Anual"] as const).map((item) => (
            <Button
              key={item}
              onClick={() => setPeriodo(item)}
              variant={periodo === item ? "contained" : "text"}
              sx={{
                color: periodo === item ? "#000" : "#fff",
                backgroundColor: periodo === item ? "#fff" : "transparent",
                borderRadius: 2,

                fontWeight: 500,
                "&:hover": {
                  backgroundColor: periodo === item ? "#fff" : "rgba(255,255,255,0.1)",
                },
              }}
            >
              {item}
            </Button>
          ))}
        </Box>
        <Box sx={{ display: "flex", flexDirection: { xs: "column", xl: "row" }, flexWrap: "wrap", gap: 2, m: 2, alignItems: "flex-end" }}>
          <TextField
            type="date"
            label="Desde"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            slotProps={{
              inputLabel: { shrink: true },
            }}
            variant="outlined"
            sx={filtroItemStyles}
          />
          <TextField
            type="date"
            label="Hasta"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            slotProps={{
              inputLabel: { shrink: true },
            }}
            variant="outlined"
            sx={filtroItemStyles}
          />
          <FormControl variant="outlined" sx={[filtroItemStyles, { minWidth: 200 }]}>
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
              sx={{ color: "#fff" }}
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
          <FormControl variant="outlined" sx={[filtroItemStyles, { minWidth: 200 }]}>
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
              sx={{ color: "#fff" }}
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
        </Box>
        <Button
          sx={{ height: "50px", mb: { xs: 3, lg: 0 }, fontSize: { xs: "10px", sm: "14px", backgroundColor: "#0166FF", borderRadius: 10 } }}
          variant="contained"
          color="primary"
          onClick={() =>
            exportDashboardToExcel({
              tarjetas: tarjetasExport,
              lineChart: lineChartData,
              pieChart: pieChartData,
            })
          }
        >
          Descargar Informe
        </Button>
      </Box>

      <Grid container spacing={2} mb={1}>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI title="Actuaciones" value={actu?.total ?? "—"} periodo={periodo} icon={""} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI title="Con contraproducencia" value={actu?.con_contraproducencia ?? "—"} periodo={periodo} icon={""} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI title="Sin contraproducencia" value={actu?.sin_contraproducencia ?? "—"} periodo={periodo} icon={""} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI
            title="Pendientes (mapa)"
            value={data?.mapa_operativo.pendientes_total ?? "—"}
            periodo={periodo}
            icon={""}
          />
        </Grid>
      </Grid>
      <Grid container spacing={2} mb={2}>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI
            title="Cola planificable"
            value={data?.mapa_operativo.pendientes_cola ?? "—"}
            periodo={periodo}
            icon={""}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI
            title="En ruta (completar trabajo)"
            value={data?.mapa_operativo.pendientes_completar_trabajo ?? "—"}
            periodo={periodo}
            icon={""}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI
            title="Realizados visita (mapa)"
            value={data?.mapa_operativo.realizados_visita ?? "—"}
            periodo={periodo}
            icon={""}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }}>
          <KPI
            title="Ítems ruta (global)"
            value={data?.ruta_items_ejecucion.total ?? "—"}
            periodo={periodo}
            icon={""}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 8 }}>
          <ChartCard title={`Actas labradas ${periodo} (tendencia — demo)`}>
            <ActuacionesMensualesChart periodo={periodo} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <ChartCard title={`Kilos decomisados (${desde} → ${hasta})`}>
            <DecomisoMensualChart decomisoKg={data?.decomiso_kg ?? null} loading={loading} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 7 }}>
          <ChartCard title={`Top contraproducencias (${desde} → ${hasta})`}>
            <DashboardContraproducenciasTop items={data?.contraproducencias_top ?? []} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <ChartCard title={`Actas por tipo (${desde} → ${hasta})`}>
            <DistribucionTipoChart actas={actas} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12 }}>
          <ChartCard title={`Top rubros por actuaciones (${desde} → ${hasta})`}>
            <TopRubrosChart items={data?.top_rubros ?? []} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12 }}>
          <ChartCard title={`Ítems de ruta — ejecución (informativo: por fecha de ruta publicada; sin filtro distrito/inspector; ≠ realizados del mapa)`}>
            {data ? (
              <DashboardRutaItemsResumen data={data.ruta_items_ejecucion} />
            ) : (
              <Typography variant="body2" color="rgba(255,255,255,0.6)" sx={{ py: 2 }}>
                {loading ? "Cargando…" : "Sin datos."}
              </Typography>
            )}
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 8 }}>
          <ChartCard title={`Ranking inspectores ${periodo} (demo)`}>
            <RankingInspectores data={inspectores} />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <ChartCard title={`Comparación por turno ${periodo} (demo)`}>
            <ComparacionTurnoChart />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <ChartCard title="Resueltos por expediente (demo)">
            <PipelineChart />
          </ChartCard>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <ChartCard title={`Actuaciones sin / con contraproducencia (${desde} → ${hasta})`}>
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
