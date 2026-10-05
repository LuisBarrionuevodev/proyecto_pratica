import {
  Box,
  Button,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Tab,
  Tooltip,
  Typography,
} from "@mui/material";
import CalendarMonthOutlinedIcon from "@mui/icons-material/CalendarMonthOutlined";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";
import { mergeSx } from "../../../utils/muiSx";
import { useEffect, useMemo, useRef, useState } from "react";

import { downloadDashboardPdf } from "../../../documentos/dashboard/downloadDashboardPdf";
import { buildDashboardExportPayload } from "../utils/buildDashboardExportPayload";
import { functionalPageShellSx } from "../../../styles/functionalPageShell";
import { moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../../styles/GlassStyles";
import { dashboardPeriodTabsSx } from "../../../styles/DashboardStyles";
import { TableExportButtonStyles } from "../../../styles/TablasStyle";
import { filtroItemStyles } from "../../Actuaciones/styles/filtroStyles";
import { fetchDistritosCatalogo } from "../../../api/geolocalizacionApi";
import { fetchInspectores } from "../../../api/gridApi";
import { useIndicadoresEjecutivo } from "../hooks/useIndicadoresEjecutivo";
import { useIndicadoresNoRealizadas } from "../hooks/useIndicadoresNoRealizadas";
import { useIndicadoresProductividad } from "../hooks/useIndicadoresProductividad";
import { useIndicadoresRiesgo } from "../hooks/useIndicadoresRiesgo";
import { useIndicadoresFiltros } from "../hooks/useIndicadoresFiltros";
import { OperativoPeriodoLabel } from "../../../components/OperativoPeriodoLabel";
import { isDashboardSectionReady } from "../utils/dashboardSectionReady";
import { calcTotalNoRealizadas } from "../utils/noRealizadasContraproducencias";
import { DashboardIndicadoresPageLoader } from "./DashboardIndicadoresPageLoader";
import { DashboardIndicadoresRefreshingOverlay } from "./DashboardIndicadoresRefreshingOverlay";
import { DashboardActasPorTipoSection } from "./DashboardActasPorTipoSection";
import { DashboardEjecutivoSection } from "./DashboardEjecutivoSection";
import { DashboardNoRealizadasSection } from "./DashboardNoRealizadasSection";
import { DashboardProductividadSectionLazy } from "./DashboardProductividadSectionLazy";
import { DashboardRiesgoSection } from "./DashboardRiesgoSection";
import { DashboardSectionGate } from "./DashboardSectionGate";
import { IndicadoresMonthPickerDialog } from "./IndicadoresMonthPickerDialog";
import { ResponsiveScrollableTabs } from "../../../ui";
import { useAppSession } from "../../../auth/AppSessionProvider";
import { normalizeAppRole } from "../../../auth/roles";

const dashCompactFiltroSx = mergeSx(filtroItemStyles, {
  minWidth: 0,
  width: { xs: "100%", sm: "auto" },
  flex: { xs: "1 1 100%", lg: "0 0 auto" },
  "& .MuiOutlinedInput-root": {
    width: { xs: "100%", lg: 156 },
  },
});

/**
 * Pendiente D1d.12 — Tribunal de falta (no implementar en este PR):
 * cohorte por inicio de trámite, comprobaciones/multas en rango, respuestas del tribunal
 * (ratificación decomiso, verificar e informar, ratificación clausura, etc.) y ejecución exitosa.
 * Requiere relevamiento y endpoints propios.
 */

const Panel = () => {
  const { role: sessionRole } = useAppSession();
  const appRole = normalizeAppRole(sessionRole);
  const isInspectorIndicadores = appRole === "relevador";

  const [monthPickerOpen, setMonthPickerOpen] = useState(false);
  const [distritoOptions, setDistritoOptions] = useState<{ id: number; nombre: string }[]>([]);
  const [inspectorOptions, setInspectorOptions] = useState<{ id: number; nombre: string }[]>([]);

  const {
    periodos,
    periodo,
    setPeriodo,
    monthOverride,
    applyMonthSelection,
    clearMonthOverride,
    distritoId,
    setDistritoId,
    inspectorId,
    setInspectorId,
    indicadoresParams,
    periodoUiLabel,
    monthOverrideActive,
    periodoTabIndex,
    desde,
    hasta,
  } = useIndicadoresFiltros(isInspectorIndicadores);

  useEffect(() => {
    if (isInspectorIndicadores) return;
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
  }, [isInspectorIndicadores]);

  useEffect(() => {
    if (isInspectorIndicadores) return;
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
  }, [isInspectorIndicadores]);

  const {
    data: ejecutivoData,
    loading: ejecutivoLoading,
    error: ejecutivoError,
  } = useIndicadoresEjecutivo(indicadoresParams);

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
    return calcTotalNoRealizadas(noRealizadasData);
  }, [noRealizadasData]);

  const distritoLabel = useMemo(() => {
    if (distritoId === "") return "Todos";
    const d = distritoOptions.find((x) => String(x.id) === distritoId);
    return d?.nombre ?? distritoId;
  }, [distritoId, distritoOptions]);

  const inspectorLabel = useMemo(() => {
    if (inspectorId === "") return "Todos";
    const i = inspectorOptions.find((x) => String(x.id) === inspectorId);
    return i?.nombre ?? inspectorId;
  }, [inspectorId, inspectorOptions]);

  const periodoLabelForExport = monthOverrideActive
    ? periodoUiLabel
    : `${periodo} (${desde} → ${hasta})`;

  const exportPayload = useMemo(
    () =>
      buildDashboardExportPayload({
        periodoLabel: periodoLabelForExport,
        distritoLabel,
        inspectorLabel,
        ejecutivo: ejecutivoData ?? null,
        riesgo: riesgoData ?? null,
        noRealizadas: noRealizadasData ?? null,
        noRealizadasTotal,
        productividad: productividadData ?? null,
      }),
    [
      periodoLabelForExport,
      distritoLabel,
      inspectorLabel,
      ejecutivoData,
      riesgoData,
      noRealizadasData,
      noRealizadasTotal,
      productividadData,
    ]
  );

  const hasExportData = exportPayload.resumenKpis.length > 0;

  const ejecutivoReady = isDashboardSectionReady(ejecutivoData, ejecutivoError);
  const riesgoReady = isDashboardSectionReady(riesgoData, riesgoError);
  const noRealizadasReady = isDashboardSectionReady(noRealizadasData, noRealizadasError);
  const productividadReady = isDashboardSectionReady(productividadData, productividadError);

  const anySectionReady =
    ejecutivoReady ||
    riesgoReady ||
    noRealizadasReady ||
    productividadReady;

  const [initialLoadDone, setInitialLoadDone] = useState(false);
  const hasEverBeenLoading = useRef(false);

  const isAnyLoading =
    ejecutivoLoading ||
    riesgoLoading ||
    noRealizadasLoading ||
    productividadLoading;

  useEffect(() => {
    if (isAnyLoading) {
      hasEverBeenLoading.current = true;
    }
  }, [isAnyLoading]);

  useEffect(() => {
    if (initialLoadDone) return;
    if (anySectionReady || (hasEverBeenLoading.current && !isAnyLoading)) {
      setInitialLoadDone(true);
    }
  }, [initialLoadDone, anySectionReady, isAnyLoading]);

  const showGlobalLoader = !initialLoadDone && !anySectionReady;
  const isRefreshing = initialLoadDone && isAnyLoading;
  const anyBlockingLoad = isAnyLoading;

  return (
    <Box
      data-testid="dashboard-panel"
      data-inspector-indicadores={isInspectorIndicadores ? "true" : undefined}
      sx={mergeSx(functionalPageShellSx, { overflowX: "hidden", minWidth: 0 })}
    >
      <Paper
        elevation={0}
        sx={{
          ...moduleSlicesPanelPaperSx,
          flexDirection: "column",
          alignItems: "stretch",
          gap: { xs: 1.25, md: 1 },
          px: { xs: 0.5, sm: 1 },
          minWidth: 0,
          maxWidth: "100%",
          overflow: "hidden",
        }}
      >
        <Box
          data-testid="dashboard-indicadores-toolbar"
          sx={{
            display: "flex",
            flexDirection: { xs: "column", lg: "row" },
            alignItems: { lg: "center" },
            justifyContent: { lg: "space-between" },
            gap: { xs: 1.25, lg: 1 },
            flexWrap: "wrap",
            minWidth: 0,
            width: "100%",
          }}
        >
          <ResponsiveScrollableTabs
            withGlassBar={false}
            value={periodoTabIndex}
            onChange={(_, v) => setPeriodo(periodos[v] ?? "Mensual")}
            sx={mergeSx(moduleSlicesTabsSx, dashboardPeriodTabsSx, {
              width: { xs: "100%", lg: "auto" },
              minWidth: 0,
              flex: { lg: "1 1 auto" },
              maxWidth: { lg: "min(520px, 55%)" },
            })}
          >
            {periodos.map((p) => (
              <Tab key={p} label={p} />
            ))}
          </ResponsiveScrollableTabs>

          <Box
            sx={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: 1,
              width: { xs: "100%", lg: "auto" },
              minWidth: 0,
              justifyContent: { xs: "flex-start", lg: "flex-end" },
              flex: { lg: "0 1 auto" },
            }}
          >
            {!isInspectorIndicadores ? (
              <>
                <FormControl variant="outlined" size="small" sx={dashCompactFiltroSx}>
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
                <FormControl variant="outlined" size="small" sx={dashCompactFiltroSx}>
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
              </>
            ) : null}

            <Button
              variant="outlined"
              size="small"
              startIcon={<CalendarMonthOutlinedIcon />}
              onClick={() => setMonthPickerOpen(true)}
              sx={{ whiteSpace: "nowrap", flexShrink: 0 }}
            >
              Elegir mes
            </Button>

            {monthOverrideActive ? (
              <Chip
                label={periodoUiLabel}
                size="small"
                onDelete={clearMonthOverride}
                color="primary"
                variant="outlined"
                sx={{ maxWidth: { xs: "100%" } }}
              />
            ) : null}

            {!isInspectorIndicadores ? (
              <Tooltip
                title={
                  hasExportData
                    ? "Informe PDF institucional del período seleccionado."
                    : "Cargá indicadores antes de exportar."
                }
              >
                <span>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<PictureAsPdfOutlinedIcon />}
                    disabled={!hasExportData || anyBlockingLoad}
                    onClick={() =>
                      downloadDashboardPdf({
                        payload: exportPayload,
                        desde: indicadoresParams.desde,
                        hasta: indicadoresParams.hasta,
                        distrito_id: indicadoresParams.distrito_id,
                        inspector_id: indicadoresParams.inspector_id,
                      })
                    }
                    sx={{
                      ...TableExportButtonStyles,
                      fontWeight: 700,
                      whiteSpace: "nowrap",
                      flexShrink: 0,
                    }}
                  >
                    Exportar PDF
                  </Button>
                </span>
              </Tooltip>
            ) : null}
          </Box>
        </Box>

        {!isInspectorIndicadores ? (
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.75rem", lineHeight: 1.35 }}>
            Distrito: {distritoLabel} · Inspector: {inspectorLabel}
          </Typography>
        ) : null}
      </Paper>

      <IndicadoresMonthPickerDialog
        open={monthPickerOpen}
        initialSelection={monthOverride}
        onClose={() => setMonthPickerOpen(false)}
        onApply={applyMonthSelection}
      />

      <OperativoPeriodoLabel desde={desde} hasta={hasta} />

      <Box sx={{ position: "relative", minHeight: showGlobalLoader ? 320 : undefined, minWidth: 0, width: "100%" }}>
        <DashboardIndicadoresRefreshingOverlay visible={isRefreshing} />

        {showGlobalLoader ? <DashboardIndicadoresPageLoader /> : null}

        {!showGlobalLoader ? (
          <>
            <DashboardSectionGate
              title="Overview operativo"
              first
              loading={ejecutivoLoading}
              ready={ejecutivoReady}
              loadingMessage="Cargando overview..."
            >
              <DashboardEjecutivoSection
                data={ejecutivoData}
                noRealizadasTotal={noRealizadasTotal}
                loading={ejecutivoLoading}
                error={ejecutivoError}
              />
            </DashboardSectionGate>

            <DashboardSectionGate
              title="Actas labradas por tipo"
              loading={ejecutivoLoading}
              ready={ejecutivoReady}
              loadingMessage="Cargando actas por tipo..."
            >
              <DashboardActasPorTipoSection
                actas={ejecutivoData?.actas_por_tipo}
                loading={ejecutivoLoading}
                error={ejecutivoError}
              />
            </DashboardSectionGate>

            <DashboardSectionGate
              title="Riesgo bromatológico"
              loading={riesgoLoading}
              ready={riesgoReady}
              loadingMessage="Cargando riesgo..."
            >
              <DashboardRiesgoSection
                data={riesgoData}
                mercaderiaDecomisadaKg={ejecutivoData?.kpis.mercaderia_decomisada_kg}
                loading={riesgoLoading}
                error={riesgoError}
              />
            </DashboardSectionGate>

            <DashboardSectionGate
              title="No realizadas"
              loading={noRealizadasLoading}
              ready={noRealizadasReady}
              loadingMessage="Cargando no realizadas..."
            >
              <DashboardNoRealizadasSection
                data={noRealizadasData}
                loading={noRealizadasLoading}
                error={noRealizadasError}
              />
            </DashboardSectionGate>

            <DashboardSectionGate
              title="Productividad"
              loading={productividadLoading}
              ready={productividadReady}
              loadingMessage="Cargando productividad..."
            >
              <DashboardProductividadSectionLazy
                data={productividadData}
                loading={productividadLoading}
                error={productividadError}
              />
            </DashboardSectionGate>
          </>
        ) : null}
      </Box>
    </Box>
  );
};

export default Panel;
