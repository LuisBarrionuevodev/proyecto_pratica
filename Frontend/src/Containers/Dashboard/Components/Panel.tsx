import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Tab,
  Tabs,
  Tooltip,
} from "@mui/material";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";
import type { SxProps, Theme } from "@mui/material/styles";
import { useEffect, useMemo, useState } from "react";

import { downloadDashboardPdf } from "../../../documentos/dashboard/downloadDashboardPdf";
import { buildDashboardExportPayload } from "../utils/buildDashboardExportPayload";
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
import { isDashboardSectionReady } from "../utils/dashboardSectionReady";
import { calcTotalNoRealizadas } from "../utils/noRealizadasContraproducencias";
import { DashboardIndicadoresPageLoader } from "./DashboardIndicadoresPageLoader";
import { DashboardIndicadoresRefreshingOverlay } from "./DashboardIndicadoresRefreshingOverlay";
import { DashboardActasPorTipoSection } from "./DashboardActasPorTipoSection";
import { DashboardEjecutivoSection } from "./DashboardEjecutivoSection";
import { DashboardPendientesSection } from "./DashboardPendientesSection";
import { DashboardNoRealizadasSection } from "./DashboardNoRealizadasSection";
import { DashboardProductividadSectionLazy } from "./DashboardProductividadSectionLazy";
import { DashboardRiesgoSection } from "./DashboardRiesgoSection";
import { DashboardSectionGate } from "./DashboardSectionGate";

const PERIODOS: Periodo[] = ["Semanal", "Mensual", "Trimestral", "Anual"];

const dashFiltroFormSx: SxProps<Theme> = [
  filtroItemStyles,
  { minWidth: { xs: "100%", sm: 168 }, flex: { sm: "0 1 168px" } },
];

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

  const pendientesParams = useMemo(() => {
    if (distritoId === "") return {};
    return { distrito_id: Number(distritoId) };
  }, [distritoId]);

  const {
    data: ejecutivoData,
    loading: ejecutivoLoading,
    error: ejecutivoError,
  } = useIndicadoresEjecutivo(indicadoresParams);

  const {
    data: pendientesData,
    loading: pendientesLoading,
    error: pendientesError,
  } = useIndicadoresPendientes(pendientesParams);

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

  const exportPayload = useMemo(
    () =>
      buildDashboardExportPayload({
        periodoLabel: `${periodo} (${desde} → ${hasta})`,
        distritoLabel,
        inspectorLabel,
        ejecutivo: ejecutivoData ?? null,
        pendientes: pendientesData ?? null,
        riesgo: riesgoData ?? null,
        noRealizadas: noRealizadasData ?? null,
        noRealizadasTotal,
        productividad: productividadData ?? null,
      }),
    [
      periodo,
      desde,
      hasta,
      distritoLabel,
      inspectorLabel,
      ejecutivoData,
      pendientesData,
      riesgoData,
      noRealizadasData,
      noRealizadasTotal,
      productividadData,
    ]
  );

  const hasExportData = exportPayload.resumenKpis.length > 0;

  const periodoTabIndex = PERIODOS.indexOf(periodo);

  const ejecutivoReady = isDashboardSectionReady(ejecutivoData, ejecutivoError);
  const pendientesReady = isDashboardSectionReady(pendientesData, pendientesError);
  const riesgoReady = isDashboardSectionReady(riesgoData, riesgoError);
  const noRealizadasReady = isDashboardSectionReady(noRealizadasData, noRealizadasError);
  const productividadReady = isDashboardSectionReady(productividadData, productividadError);

  const showGlobalLoader =
    !ejecutivoReady &&
    ejecutivoLoading &&
    !pendientesReady &&
    pendientesLoading &&
    !riesgoReady &&
    riesgoLoading &&
    !noRealizadasReady &&
    noRealizadasLoading &&
    !productividadReady &&
    productividadLoading;

  const isAnyLoading =
    ejecutivoLoading ||
    pendientesLoading ||
    riesgoLoading ||
    noRealizadasLoading ||
    productividadLoading;

  const isRefreshing = isAnyLoading && !showGlobalLoader;

  const anyBlockingLoad = isAnyLoading;

  return (
    <Box sx={functionalPageShellSx}>
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
          <FormControl variant="outlined" sx={dashFiltroFormSx}>
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
          <FormControl variant="outlined" sx={dashFiltroFormSx}>
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
              hasExportData
                ? "Informe PDF institucional del período seleccionado."
                : "Cargá indicadores antes de exportar."
            }
          >
            <span>
              <Button
                variant="outlined"
                startIcon={<PictureAsPdfOutlinedIcon />}
                disabled={!hasExportData || anyBlockingLoad}
                onClick={() =>
                  downloadDashboardPdf({
                    payload: exportPayload,
                    desde,
                    hasta,
                  })
                }
                sx={{
                  ...TableExportButtonStyles,
                  fontWeight: 700,
                  alignSelf: { xs: "stretch", sm: "center" },
                  whiteSpace: "nowrap",
                }}
              >
                Exportar PDF
              </Button>
            </span>
          </Tooltip>
          </Box>
      </Paper>

      <Box sx={{ position: "relative", minHeight: showGlobalLoader ? 320 : undefined }}>
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
              title="Operativo / Pendientes actuales"
              loading={pendientesLoading}
              ready={pendientesReady}
              loadingMessage="Cargando pendientes..."
            >
              <DashboardPendientesSection
                data={pendientesData}
                loading={pendientesLoading}
                error={pendientesError}
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
