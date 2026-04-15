import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ClearIcon from "@mui/icons-material/Clear";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";
import {
  Alert,
  Box,
  CircularProgress,
  IconButton,
  Paper,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_TableOptions,
} from "material-react-table";

import {
  createExpedienteDesdeActuacion,
  getActuacionesPendientesExpediente,
  postSyncNotificacionesVencidas,
  type IActuacionesPendientesItem,
  type ICreateExpedienteRequest,
  type ISyncNotificacionesVencidasResponse,
} from "../../api/actuacionesPendientesApi";
import { getCurrentMonthRange } from "../../utils/dateRange";
import { functionalPageShellSx } from "../../styles/functionalPageShell";
import { DARK_TABLE_CONFIG, MRT_READ_ONLY_BANDEJA } from "../Actuaciones/styles/actuacionesTableStyles";
import {
  alertBaseStyles,
  COLORS,
  filtroButtonPrimaryStyles,
  filtroButtonSecondaryStyles,
  filtroButtonsStyles,
  filtroContainerStyles,
  filtroGridStyles,
  filtroItemStyles,
  filtroTitleStyles,
  metaInfoStyles,
  metaItemStyles,
  moduleContentColumnSx,
} from "../Actuaciones/styles/filtroStyles";
import { GLASS_COLORS, glassSecondaryTabsSx, glassTabsSecondaryPanelBarSx } from "../../styles/GlassStyles";
import { fetchDistritosCatalogo, type DistritoCatalogoItem } from "../../api/geolocalizacionApi";
import { AppButton, AppSelect, AppTextField } from "../../ui";
import {
  countByPlazoSlice,
  matchesPlazoSlice,
  sliceLabel,
  type PlazoOperativoSlice,
} from "./gestionNotificacionPlazo";
import {
  NotificacionDetalleDocumentalDialog,
  type NotificacionDetalleModalVariant,
} from "./components/NotificacionDetalleDocumentalDialog";

/** Operativas primero; `total` = Historial (documental), al final. */
const PLAZO_TAB_ORDER: PlazoOperativoSlice[] = ["en_plazo", "por_vencer", "vencidas_o_hoy", "total"];

type HistPeriodMode = "month" | "range";

const MESES_OPTS = Array.from({ length: 12 }, (_, i) => ({
  value: String(i + 1),
  label: String(i + 1),
}));

function yearOptions(center: number): { value: string; label: string }[] {
  const out: { value: string; label: string }[] = [];
  for (let y = center - 5; y <= center + 2; y++) out.push({ value: String(y), label: String(y) });
  return out;
}

type HistorialAppliedPeriod =
  | { kind: "month"; mes: number; anio: number }
  | { kind: "range"; desde: string; hasta: string };

function contribuyenteText(row: IActuacionesPendientesItem): string {
  const a = (row.contrib_apellido ?? "").trim();
  const n = (row.contrib_nombre ?? "").trim();
  const t = [a, n].filter(Boolean).join(", ");
  return t || "—";
}

function domicilioText(row: IActuacionesPendientesItem): string {
  const c = (row.calle ?? "").trim();
  const n = (row.numero ?? "").trim();
  const t = [c, n].filter(Boolean).join(" ");
  return t || "—";
}

function motivosNotif(row: IActuacionesPendientesItem): string {
  const parts = [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3].filter(
    (s): s is string => Boolean(s && String(s).trim())
  );
  return parts.join(", ") || "—";
}

function diasRestantesCell(row: IActuacionesPendientesItem): string {
  if (row.dias_restantes === null || row.dias_restantes === undefined) return "—";
  return String(row.dias_restantes);
}

function plazosOtorgadosCell(row: IActuacionesPendientesItem): string {
  if (row.plazos_otorgados === null || row.plazos_otorgados === undefined) return "—";
  return String(row.plazos_otorgados);
}

/** Celda truncada con tooltip (bandeja compacta). */
function EllipsisTableCell({ value }: { value: string }) {
  const body = (
    <Box
      component="span"
      sx={{
        display: "block",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
        maxWidth: "100%",
        typography: "body2",
      }}
    >
      {value}
    </Box>
  );
  if (!value || value === "—") return body;
  return (
    <Tooltip title={value} placement="top-start" enterDelay={400}>
      {body}
    </Tooltip>
  );
}

function trimToNull(s: string): string | null {
  const t = s.trim();
  return t.length > 0 ? t : null;
}

type NotificacionBandejaTableProps = {
  rows: IActuacionesPendientesItem[];
  loading: boolean;
  columns: MRT_ColumnDef<IActuacionesPendientesItem>[];
  toolbar?: () => React.ReactNode;
  /** Misma acotación de altura que Recorrido bajo panel documental (scroll del layout). */
  documentalListViewport?: boolean;
};

/** Tabla MRT reutilizable (operativa vs historial). */
function NotificacionBandejaTable({
  rows,
  loading,
  columns,
  toolbar,
  documentalListViewport,
}: NotificacionBandejaTableProps) {
  const documentalMrtLayout: Partial<MRT_TableOptions<IActuacionesPendientesItem>> | undefined = documentalListViewport
    ? {
        muiTablePaperProps: {
          sx: {
            ...((DARK_TABLE_CONFIG.muiTablePaperProps as { sx?: Record<string, unknown> })?.sx ?? {}),
            width: "100%",
            maxWidth: "100%",
            minWidth: 0,
          },
        },
        muiTableContainerProps: {
          sx: {
            ...((DARK_TABLE_CONFIG.muiTableContainerProps as { sx?: Record<string, unknown> })?.sx ?? {}),
            minWidth: 0,
            maxWidth: "100%",
            maxHeight: { xs: "min(45vh, 360px)", sm: "min(52vh, 440px)", md: "min(58vh, 520px)" },
          },
        },
      }
    : undefined;

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...MRT_READ_ONLY_BANDEJA,
    ...documentalMrtLayout,
    columns,
    data: rows,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    renderTopToolbarCustomActions: toolbar,
    state: {
      isLoading: loading,
      showProgressBars: loading,
    },
  });
  return <MaterialReactTable table={table} />;
}

/**
 * Bandeja: operativa con GET omitir_rango_fecha; historial con mes/año tras aplicar filtro.
 */
const GestionNotificacionPage = () => {
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const defaultMonthYear = useMemo(() => {
    const d = new Date(`${defaultRange.desde}T12:00:00`);
    return { mes: d.getMonth() + 1, anio: d.getFullYear() };
  }, [defaultRange.desde]);

  const [items, setItems] = useState<IActuacionesPendientesItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plazoSlice, setPlazoSlice] = useState<PlazoOperativoSlice>("en_plazo");

  const [histPeriodMode, setHistPeriodMode] = useState<HistPeriodMode>("month");
  const [histMes, setHistMes] = useState(defaultMonthYear.mes);
  const [histAnio, setHistAnio] = useState(defaultMonthYear.anio);
  const [histDesde, setHistDesde] = useState<string | null>(defaultRange.desde);
  const [histHasta, setHistHasta] = useState<string | null>(defaultRange.hasta);
  const [histDistritoId, setHistDistritoId] = useState<number | "">("");
  const [histContribQ, setHistContribQ] = useState("");
  const [histCalleQ, setHistCalleQ] = useState("");
  const [histNumNotif, setHistNumNotif] = useState("");
  const [histMotivoQ, setHistMotivoQ] = useState("");
  const [distritosHistorial, setDistritosHistorial] = useState<DistritoCatalogoItem[]>([]);
  const [historialFiltroAplicado, setHistorialFiltroAplicado] = useState(false);
  const [historialRows, setHistorialRows] = useState<IActuacionesPendientesItem[]>([]);
  const [historialLoading, setHistorialLoading] = useState(false);
  const [historialError, setHistorialError] = useState<string | null>(null);
  const [historialMeta, setHistorialMeta] = useState<{
    total: number;
    desde: string | null;
    hasta: string | null;
  } | null>(null);
  const [historialApplied, setHistorialApplied] = useState<{
    period: HistorialAppliedPeriod;
    distritoId: number | null;
    contribuyenteQ: string | null;
    calleQ: string | null;
    numeroNotificacion: string | null;
    motivoQ: string | null;
  } | null>(null);

  const distritoSelectOptionsHistorial = useMemo(
    () => [
      { value: "", label: "Todos los distritos" },
      ...distritosHistorial.map((d) => ({ value: String(d.id), label: d.nombre })),
    ],
    [distritosHistorial]
  );

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const r = await fetchDistritosCatalogo();
        if (!cancelled) setDistritosHistorial(r.items ?? []);
      } catch {
        if (!cancelled) setDistritosHistorial([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const prevPlazoSliceRef = useRef<PlazoOperativoSlice>(plazoSlice);

  const [selected, setSelected] = useState<IActuacionesPendientesItem | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalVariant, setModalVariant] = useState<NotificacionDetalleModalVariant>("documental");
  const [expNumero, setExpNumero] = useState("");
  const [expFecha, setExpFecha] = useState(defaultRange.hasta);
  const [prorrogaDias, setProrrogaDias] = useState("0");
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [modalApiError, setModalApiError] = useState<string | null>(null);

  const [syncLoading, setSyncLoading] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState<
    | null
    | { kind: "success"; metrics: ISyncNotificacionesVencidasResponse }
    | { kind: "error"; message: string }
  >(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getActuacionesPendientesExpediente(undefined, undefined, "notificacion", null, {
        omitirRangoFecha: true,
      });
      setItems(resp.items);
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setError(detail || "Error al cargar la bandeja");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  /** Al volver a entrar en Historial desde otra pestaña, se pide de nuevo aplicar filtro (sin tabla inicial). */
  useEffect(() => {
    const prev = prevPlazoSliceRef.current;
    prevPlazoSliceRef.current = plazoSlice;
    if (plazoSlice === "total" && prev !== "total") {
      setHistorialFiltroAplicado(false);
      setHistorialRows([]);
      setHistorialError(null);
      setHistorialApplied(null);
      setHistorialMeta(null);
    }
  }, [plazoSlice]);

  const loadHistorialDesdeFiltro = useCallback(async () => {
    const distritoId = histDistritoId === "" ? null : histDistritoId;
    const docOpts = {
      contribuyenteQ: trimToNull(histContribQ) ?? undefined,
      calleQ: trimToNull(histCalleQ) ?? undefined,
      numeroNotificacion: trimToNull(histNumNotif) ?? undefined,
      motivoQ: trimToNull(histMotivoQ) ?? undefined,
    };

    if (histPeriodMode === "month") {
      if (!Number.isFinite(histMes) || histMes < 1 || histMes > 12 || !Number.isFinite(histAnio) || histAnio < 1970) {
        setHistorialError("Indicá un mes y año válidos.");
        return;
      }
    } else {
      if (!histDesde || !histHasta) {
        setHistorialError("Completá las fechas desde y hasta.");
        return;
      }
      if (histDesde > histHasta) {
        setHistorialError("La fecha desde no puede ser posterior a la fecha hasta.");
        return;
      }
    }

    setHistorialLoading(true);
    setHistorialError(null);
    try {
      const resp =
        histPeriodMode === "month"
          ? await getActuacionesPendientesExpediente(undefined, undefined, "notificacion", distritoId, {
              mes: histMes,
              anio: histAnio,
              ...docOpts,
            })
          : await getActuacionesPendientesExpediente(histDesde, histHasta, "notificacion", distritoId, docOpts);

      const period: HistorialAppliedPeriod =
        histPeriodMode === "month"
          ? { kind: "month", mes: histMes, anio: histAnio }
          : { kind: "range", desde: histDesde!, hasta: histHasta! };

      setHistorialRows(resp.items);
      setHistorialMeta({
        total: resp.meta.total,
        desde: resp.meta.desde,
        hasta: resp.meta.hasta,
      });
      setHistorialApplied({
        period,
        distritoId,
        contribuyenteQ: trimToNull(histContribQ),
        calleQ: trimToNull(histCalleQ),
        numeroNotificacion: trimToNull(histNumNotif),
        motivoQ: trimToNull(histMotivoQ),
      });
      setHistorialFiltroAplicado(true);
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setHistorialError(detail || "Error al cargar el historial");
      setHistorialRows([]);
      setHistorialFiltroAplicado(false);
      setHistorialApplied(null);
      setHistorialMeta(null);
    } finally {
      setHistorialLoading(false);
    }
  }, [
    histPeriodMode,
    histMes,
    histAnio,
    histDesde,
    histHasta,
    histDistritoId,
    histContribQ,
    histCalleQ,
    histNumNotif,
    histMotivoQ,
  ]);

  const recargarHistorialSiAplica = useCallback(async () => {
    if (!historialFiltroAplicado || !historialApplied) return;
    setHistorialLoading(true);
    setHistorialError(null);
    try {
      const doc = {
        contribuyenteQ: historialApplied.contribuyenteQ ?? undefined,
        calleQ: historialApplied.calleQ ?? undefined,
        numeroNotificacion: historialApplied.numeroNotificacion ?? undefined,
        motivoQ: historialApplied.motivoQ ?? undefined,
      };
      const resp =
        historialApplied.period.kind === "month"
          ? await getActuacionesPendientesExpediente(
              undefined,
              undefined,
              "notificacion",
              historialApplied.distritoId,
              { mes: historialApplied.period.mes, anio: historialApplied.period.anio, ...doc }
            )
          : await getActuacionesPendientesExpediente(
              historialApplied.period.desde,
              historialApplied.period.hasta,
              "notificacion",
              historialApplied.distritoId,
              doc
            );
      setHistorialRows(resp.items);
      setHistorialMeta({
        total: resp.meta.total,
        desde: resp.meta.desde,
        hasta: resp.meta.hasta,
      });
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setHistorialError(detail || "Error al recargar el historial");
    } finally {
      setHistorialLoading(false);
    }
  }, [historialFiltroAplicado, historialApplied]);

  const handleSyncNotificacionesVencidas = useCallback(async () => {
    setSyncLoading(true);
    setSyncFeedback(null);
    try {
      const metrics = await postSyncNotificacionesVencidas();
      setSyncFeedback({ kind: "success", metrics });
      await loadData();
      if (historialFiltroAplicado) {
        await recargarHistorialSiAplica();
      }
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string }; status?: number } }).response?.data?.detail
          : null;
      const status =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { status?: number } }).response?.status
          : undefined;
      if (status === 429) {
        setSyncFeedback({
          kind: "error",
          message: typeof detail === "string" ? detail : "Demasiadas solicitudes. Probá más tarde.",
        });
      } else {
        setSyncFeedback({
          kind: "error",
          message: typeof detail === "string" ? detail : "No se pudo sincronizar.",
        });
      }
    } finally {
      setSyncLoading(false);
    }
  }, [loadData, historialFiltroAplicado, recargarHistorialSiAplica]);

  const notificacionRows = useMemo(
    () => items.filter((r) => r.source_type === "NOTIFICACION"),
    [items]
  );

  const sliceCounts = useMemo(() => countByPlazoSlice(notificacionRows), [notificacionRows]);

  const filteredRowsOperativa = useMemo(
    () => notificacionRows.filter((r) => matchesPlazoSlice(r, plazoSlice)),
    [notificacionRows, plazoSlice]
  );

  const openModal = useCallback((row: IActuacionesPendientesItem, variant: NotificacionDetalleModalVariant) => {
    setModalVariant(variant);
    setSelected(row);
    setExpNumero("");
    setExpFecha(defaultRange.hasta);
    setProrrogaDias("0");
    setFieldErrors({});
    setModalApiError(null);
    setModalOpen(true);
  }, [defaultRange.hasta]);

  const closeModal = () => {
    if (saving) return;
    setModalOpen(false);
    setSelected(null);
    setFieldErrors({});
    setModalApiError(null);
  };

  const handleSave = async () => {
    if (!selected) return;
    const next: Record<string, string> = {};
    if (!expNumero.trim()) next.expNumero = "Completá el número de expediente.";
    if (!expFecha) next.expFecha = "Completá la fecha de expediente.";
    const pr = Number(prorrogaDias);
    if (prorrogaDias.trim() !== "" && (Number.isNaN(pr) || pr < 0)) {
      next.prorrogaDias = "Indicá un número de días válido (0 o más).";
    }
    setFieldErrors(next);
    if (Object.keys(next).length > 0) return;

    setSaving(true);
    setModalApiError(null);
    try {
      const payload: ICreateExpedienteRequest = {
        expediente_numero: expNumero.trim(),
        fecha_expediente: expFecha,
        source_type: "NOTIFICACION",
        prorroga_dias: Number(prorrogaDias) || 0,
      };
      await createExpedienteDesdeActuacion(selected.id, payload);
      closeModal();
      await loadData();
      if (plazoSlice === "total" && historialFiltroAplicado) {
        await recargarHistorialSiAplica();
      }
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setModalApiError(detail || "No se pudo añadir el expediente de plazo");
    } finally {
      setSaving(false);
    }
  };

  /** Anchos reducidos para dar lugar a la columna Acción (MRT sin resize en bandeja). */
  const columnsDataCompact = useMemo<MRT_ColumnDef<IActuacionesPendientesItem>[]>(
    () => [
      {
        accessorKey: "fecha_actuacion",
        header: "Fecha",
        size: 100,
        Cell: ({ cell }) => <EllipsisTableCell value={String(cell.getValue() ?? "").trim() || "—"} />,
      },
      {
        id: "contribuyente",
        header: "Contribuyente",
        size: 132,
        accessorFn: (row) => contribuyenteText(row),
        Cell: ({ row }) => <EllipsisTableCell value={contribuyenteText(row.original)} />,
      },
      {
        id: "domicilio",
        header: "Domicilio",
        size: 148,
        accessorFn: (row) => domicilioText(row),
        Cell: ({ row }) => <EllipsisTableCell value={domicilioText(row.original)} />,
      },
      {
        id: "acta_notificacion",
        header: "Nº notificación",
        size: 108,
        accessorFn: (row) => row.acta_notificacion_num ?? "—",
        Cell: ({ row }) => (
          <EllipsisTableCell value={(row.original.acta_notificacion_num ?? "").trim() || "—"} />
        ),
      },
      {
        id: "motivos",
        header: "Motivo(s)",
        size: 124,
        accessorFn: (row) => motivosNotif(row),
        Cell: ({ row }) => <EllipsisTableCell value={motivosNotif(row.original)} />,
      },
      {
        id: "dias_restantes",
        header: "Días rest.",
        size: 88,
        accessorFn: (row) => diasRestantesCell(row),
        Cell: ({ row }) => <EllipsisTableCell value={diasRestantesCell(row.original)} />,
      },
      {
        id: "plazos_otorgados",
        header: "Plazos",
        size: 84,
        accessorFn: (row) => plazosOtorgadosCell(row),
        Cell: ({ row }) => <EllipsisTableCell value={plazosOtorgadosCell(row.original)} />,
      },
    ],
    []
  );

  const columnsOperativa = useMemo<MRT_ColumnDef<IActuacionesPendientesItem>[]>(
    () => [
      ...columnsDataCompact,
      {
        id: "acciones",
        header: "Acción",
        size: 196,
        grow: false,
        Cell: ({ row }) => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModal(row.original, "soloExpediente")}>
            Agregar expediente
          </AppButton>
        ),
      },
    ],
    [columnsDataCompact, openModal]
  );

  const columnsHistorial = useMemo<MRT_ColumnDef<IActuacionesPendientesItem>[]>(
    () => [
      ...columnsDataCompact,
      {
        id: "ver",
        header: "Acción",
        size: 128,
        grow: false,
        Cell: ({ row }) => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModal(row.original, "documental")}>
            Ver detalle
          </AppButton>
        ),
      },
    ],
    [columnsDataCompact, openModal]
  );

  const renderOperativaToolbarRefresh = useCallback(
    () => (
      <Tooltip title="Recargar bandeja">
        <span>
          <IconButton
            type="button"
            size="small"
            aria-label="Recargar bandeja"
            disabled={loading}
            onClick={() => void loadData()}
            sx={{
              color: GLASS_COLORS.textSecondary,
              "&:hover": { color: GLASS_COLORS.textPrimary, backgroundColor: GLASS_COLORS.hoverBg },
            }}
          >
            <RefreshIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
    ),
    [loading, loadData]
  );

  const renderHistorialToolbarRefresh = useCallback(
    () => (
      <Tooltip title="Recargar resultados del historial">
        <span>
          <IconButton
            type="button"
            size="small"
            aria-label="Recargar historial"
            disabled={historialLoading || !historialFiltroAplicado}
            onClick={() => void recargarHistorialSiAplica()}
            sx={{
              color: GLASS_COLORS.textSecondary,
              "&:hover": { color: GLASS_COLORS.textPrimary, backgroundColor: GLASS_COLORS.hoverBg },
            }}
          >
            <RefreshIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
    ),
    [historialLoading, historialFiltroAplicado, recargarHistorialSiAplica]
  );

  /** Contador solo para pestañas operativas (no historial). */
  const tabSuffixOperativa = useCallback(
    (slice: Exclude<PlazoOperativoSlice, "total">): string => {
      if (loading) return "…";
      return String(sliceCounts[slice]);
    },
    [loading, sliceCounts]
  );

  const mostrarTablaOperativa = plazoSlice !== "total";
  const mostrarHistorial = plazoSlice === "total";

  return (
    <Box sx={{ ...functionalPageShellSx, ...moduleContentColumnSx }}>
      <Box
        sx={{
          display: "flex",
          flexDirection: { xs: "column", sm: "row" },
          flexWrap: "wrap",
          alignItems: { xs: "stretch", sm: "flex-start" },
          gap: 2,
          pb: 1,
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <Box sx={{ flex: "1 1 280px", minWidth: 0 }}>
          <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.78)", mb: 0.75 }}>
            <strong>Sincronizar vencimientos</strong> materializa en el sistema la cola de reinspección por
            notificaciones vencidas (iniciadores para planificación). Esta tabla sigue siendo la bandeja de{" "}
            <strong>expedientes de plazo</strong> y <strong>días restantes</strong>: el resultado del sync{" "}
            <strong>no siempre cambia</strong> las filas visibles.
          </Typography>
          <Typography variant="caption" sx={{ display: "block", color: "rgba(255,255,255,0.55)", mb: 1.25 }}>
            Tras <strong>Sincronizar vencimientos</strong> correcto, la bandeja se recarga sola. El ícono de actualizar
            en la barra de la tabla solo <strong>recarga esta bandeja</strong>; no ejecuta la sincronización.
          </Typography>
          <AppButton
            dsVariant="primary"
            dsSize="sm"
            onClick={() => void handleSyncNotificacionesVencidas()}
            disabled={syncLoading || loading}
          >
            {syncLoading ? "Sincronizando…" : "Sincronizar vencimientos"}
          </AppButton>
        </Box>
      </Box>

      {syncFeedback?.kind === "success" && (
        <Alert severity="success" sx={alertBaseStyles} onClose={() => setSyncFeedback(null)}>
          Sincronización correcta. Creados: <strong>{syncFeedback.metrics.created}</strong>, elegibles:{" "}
          <strong>{syncFeedback.metrics.eligible_notificaciones}</strong>, omitidos (ya bloqueados):{" "}
          <strong>{syncFeedback.metrics.skipped_already_blocking}</strong>, colisiones idempotentes:{" "}
          <strong>{syncFeedback.metrics.collisions_idempotent}</strong>, tiempo:{" "}
          <strong>{syncFeedback.metrics.elapsed_ms}</strong> ms.
        </Alert>
      )}
      {syncFeedback?.kind === "error" && (
        <Alert severity="error" sx={alertBaseStyles} onClose={() => setSyncFeedback(null)}>
          {syncFeedback.message}
        </Alert>
      )}

      <Paper elevation={0} sx={{ ...glassTabsSecondaryPanelBarSx, width: "100%" }}>
        <Tabs
          value={plazoSlice}
          onChange={(_, v) => setPlazoSlice(v as PlazoOperativoSlice)}
          variant="scrollable"
          allowScrollButtonsMobile
          sx={glassSecondaryTabsSx}
        >
          {PLAZO_TAB_ORDER.map((slice) => (
            <Tab
              key={slice}
              value={slice}
              label={
                slice === "total"
                  ? sliceLabel(slice)
                  : `${sliceLabel(slice)} · ${tabSuffixOperativa(slice)}`
              }
            />
          ))}
        </Tabs>
      </Paper>

      {error && (
        <Alert severity="error" sx={alertBaseStyles}>
          {error}
        </Alert>
      )}

      {mostrarTablaOperativa && (
        <>
          {loading && notificacionRows.length === 0 && !error ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
              <CircularProgress size={28} sx={{ color: COLORS.primary }} />
            </Box>
          ) : (
            <Box sx={{ position: "relative", opacity: loading ? 0.65 : 1, transition: "opacity 0.2s" }}>
              {loading && notificacionRows.length > 0 && (
                <Box
                  sx={{
                    position: "absolute",
                    inset: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    zIndex: 1,
                    pointerEvents: "none",
                  }}
                >
                  <CircularProgress size={32} sx={{ color: COLORS.primary }} />
                </Box>
              )}
              <NotificacionBandejaTable
                rows={filteredRowsOperativa}
                loading={loading}
                columns={columnsOperativa}
                toolbar={renderOperativaToolbarRefresh}
              />
            </Box>
          )}
        </>
      )}

      {mostrarHistorial && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Box sx={filtroContainerStyles}>
            <Typography sx={filtroTitleStyles}>Historial — filtros documentales</Typography>
            <Typography variant="caption" sx={{ display: "block", color: "rgba(255,255,255,0.55)", mb: 1.5 }}>
              Vista documental consultiva: actuaciones con <strong>notificación pendiente de expediente de plazo</strong>{" "}
              en el período indicado. Período calendario o rango de fechas, distrito y criterios opcionales (contribuyente,
              calle, número de acta de notificación, motivos / infracción). Los textos son opcionales. Tocá{" "}
              <strong>Filtrar</strong> para cargar la tabla.
            </Typography>
            <Box sx={filtroGridStyles}>
              <Box sx={filtroItemStyles}>
                <AppSelect
                  appearance="dense"
                  fullWidth
                  label="Vista de período"
                  value={histPeriodMode}
                  onChange={(e) => setHistPeriodMode(e.target.value as HistPeriodMode)}
                  variant="outlined"
                  options={[
                    { value: "month", label: "Mes y año" },
                    { value: "range", label: "Fecha desde / hasta" },
                  ]}
                />
              </Box>
              {histPeriodMode === "month" ? (
                <>
                  <Box sx={filtroItemStyles}>
                    <AppSelect
                      appearance="dense"
                      fullWidth
                      label="Mes"
                      value={String(histMes)}
                      onChange={(e) => setHistMes(Number(e.target.value))}
                      variant="outlined"
                      options={MESES_OPTS}
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppSelect
                      appearance="dense"
                      fullWidth
                      label="Año"
                      value={String(histAnio)}
                      onChange={(e) => setHistAnio(Number(e.target.value))}
                      variant="outlined"
                      options={yearOptions(defaultMonthYear.anio)}
                    />
                  </Box>
                </>
              ) : (
                <>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      label="Desde"
                      type="date"
                      value={histDesde ?? ""}
                      onChange={(e) => setHistDesde(e.target.value || null)}
                      InputLabelProps={{ shrink: true }}
                      variant="outlined"
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      label="Hasta"
                      type="date"
                      value={histHasta ?? ""}
                      onChange={(e) => setHistHasta(e.target.value || null)}
                      InputLabelProps={{ shrink: true }}
                      variant="outlined"
                    />
                  </Box>
                </>
              )}
              <Box sx={filtroItemStyles}>
                <AppSelect
                  appearance="dense"
                  fullWidth
                  label="Distrito"
                  value={histDistritoId === "" ? "" : String(histDistritoId)}
                  onChange={(e) => {
                    const v = e.target.value;
                    setHistDistritoId(v === "" ? "" : Number(v));
                  }}
                  variant="outlined"
                  options={distritoSelectOptionsHistorial}
                />
              </Box>
              <Box sx={filtroItemStyles}>
                <AppTextField
                  appearance="dense"
                  fullWidth
                  label="Contribuyente"
                  value={histContribQ}
                  onChange={(e) => setHistContribQ(e.target.value)}
                  variant="outlined"
                />
              </Box>
              <Box sx={filtroItemStyles}>
                <AppTextField
                  appearance="dense"
                  fullWidth
                  label="Calle"
                  value={histCalleQ}
                  onChange={(e) => setHistCalleQ(e.target.value)}
                  variant="outlined"
                />
              </Box>
              <Box sx={filtroItemStyles}>
                <AppTextField
                  appearance="dense"
                  fullWidth
                  label="Nº notificación"
                  placeholder="Fragmento del acta"
                  value={histNumNotif}
                  onChange={(e) => setHistNumNotif(e.target.value)}
                  variant="outlined"
                />
              </Box>
              <Box sx={filtroItemStyles}>
                <AppTextField
                  appearance="dense"
                  fullWidth
                  label="Motivo / infracción"
                  placeholder="Texto en motivos de la notificación"
                  value={histMotivoQ}
                  onChange={(e) => setHistMotivoQ(e.target.value)}
                  variant="outlined"
                />
              </Box>
            </Box>
            <Box sx={filtroButtonsStyles}>
              <AppButton
                dsVariant="ghost"
                dsSize="sm"
                onClick={() => {
                  const r = getCurrentMonthRange();
                  const d = new Date(`${r.desde}T12:00:00`);
                  setHistPeriodMode("month");
                  setHistMes(d.getMonth() + 1);
                  setHistAnio(d.getFullYear());
                  setHistDesde(r.desde);
                  setHistHasta(r.hasta);
                  setHistDistritoId("");
                  setHistContribQ("");
                  setHistCalleQ("");
                  setHistNumNotif("");
                  setHistMotivoQ("");
                  setHistorialFiltroAplicado(false);
                  setHistorialMeta(null);
                  setHistorialRows([]);
                  setHistorialError(null);
                }}
                startIcon={<ClearIcon />}
                sx={filtroButtonSecondaryStyles}
              >
                Limpiar
              </AppButton>
              <AppButton
                dsVariant="primary"
                dsSize="sm"
                startIcon={<SearchIcon />}
                onClick={() => void loadHistorialDesdeFiltro()}
                disabled={historialLoading}
                sx={filtroButtonPrimaryStyles}
              >
                {historialLoading ? "Cargando…" : "Filtrar"}
              </AppButton>
            </Box>
          </Box>

          {historialError ? (
            <Alert severity="error" sx={alertBaseStyles} onClose={() => setHistorialError(null)}>
              {historialError}
            </Alert>
          ) : null}

          {historialLoading && (
            <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
              <CircularProgress sx={{ color: COLORS.primary }} />
            </Box>
          )}

          {!historialLoading && historialFiltroAplicado && (
            <>
              {historialMeta && (
                <Box sx={metaInfoStyles}>
                  <Typography sx={metaItemStyles}>
                    <strong>Total:</strong> {historialMeta.total}
                  </Typography>
                  <Typography sx={metaItemStyles}>
                    <strong>Mostrando:</strong> {historialRows.length} de {historialMeta.total}
                  </Typography>
                  <Typography sx={metaItemStyles}>
                    <strong>Página:</strong> 1
                  </Typography>
                  {historialMeta.desde && historialMeta.hasta && (
                    <Typography sx={metaItemStyles}>
                      <strong>Rango:</strong> {historialMeta.desde} — {historialMeta.hasta}
                    </Typography>
                  )}
                </Box>
              )}
              <Box sx={{ width: "100%", minWidth: 0, maxWidth: "100%" }}>
                <NotificacionBandejaTable
                  rows={historialRows}
                  loading={false}
                  columns={columnsHistorial}
                  toolbar={renderHistorialToolbarRefresh}
                  documentalListViewport
                />
              </Box>
            </>
          )}

          {!historialLoading && !historialFiltroAplicado && (
            <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, py: 1 }}>
              Elegí período y distrito, ajustá filtros opcionales si hace falta, y tocá <strong>Filtrar</strong> para ver
              el listado.
            </Typography>
          )}
        </Box>
      )}

      <NotificacionDetalleDocumentalDialog
        open={modalOpen}
        onClose={closeModal}
        row={selected}
        variant={modalVariant}
        expNumero={expNumero}
        onExpNumeroChange={(v) => {
          setExpNumero(v);
          setFieldErrors((f) => {
            const n = { ...f };
            delete n.expNumero;
            return n;
          });
        }}
        expFecha={expFecha}
        onExpFechaChange={(v) => {
          setExpFecha(v);
          setFieldErrors((f) => {
            const n = { ...f };
            delete n.expFecha;
            return n;
          });
        }}
        prorrogaDias={prorrogaDias}
        onProrrogaDiasChange={(v) => {
          setProrrogaDias(v);
          setFieldErrors((f) => {
            const n = { ...f };
            delete n.prorrogaDias;
            return n;
          });
        }}
        fieldErrors={fieldErrors}
        modalApiError={modalApiError}
        saving={saving}
        onGuardar={handleSave}
      />
    </Box>
  );
};

export default GestionNotificacionPage;
