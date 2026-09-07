import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ClearIcon from "@mui/icons-material/Clear";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  FormControlLabel,
  IconButton,
  Paper,
  Stack,
  Switch,
  Tab,
  Tabs,
  Tooltip,
  Typography,
  type SxProps,
  type Theme,
} from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_PaginationState,
  type MRT_TableOptions,
  type MRT_Updater,
} from "material-react-table";

import {
  createExpedienteDesdeActuacion,
  getActuacionesPendientesExpediente,
  getPendientesReinspeccionNotificacion,
  postSyncNotificacionesVencidas,
  type IActuacionesPendientesItem,
  type ICreateExpedienteRequest,
  type ISyncNotificacionesVencidasResponse,
} from "../../api/actuacionesPendientesApi";
import { getCurrentMonthRange } from "../../utils/dateRange";
import {
  buildClientPaginationSummary,
  DEFAULT_BANDEJA_CLIENT_PAGE_SIZE,
  resetClientPaginationPageIndex,
} from "../../utils/buildClientPaginationSummary";
import {
  BandejaTableSpinner,
  BANDEJA_MRT_SPINNER_LOADING_STATE,
} from "../../components/dataTable/bandejaTableLoading";
import {
  BandejaTableSummary,
  BandejaTableSummaryItem,
} from "../../components/dataTable/BandejaTableSummary";
import { contribuyenteBandejaLabel } from "../../utils/contribuyenteBandejaText";
import { formatActuacionListDomicilioLinea } from "../../utils/formatDomicilioLineaVisible";
import { functionalPageShellSx } from "../../styles/functionalPageShell";
import {
  BandejaActaChipCell,
  BandejaEllipsisCell,
  BandejaFechaYChipOtCell,
  BandejaSegmentChipsCell,
  BANDEJA_MRT_BODY_CELL_PROPS,
  splitMiddleDot,
} from "../Actuaciones/Components/bandejaTableCells";
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
  filtroSectionTitleStyles,
  filtroTitleStyles,
  moduleContentColumnSx,
} from "../Actuaciones/styles/filtroStyles";
import { GLASS_COLORS, moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../styles/GlassStyles";
import { fetchDistritosCatalogo, type DistritoCatalogoItem } from "../../api/geolocalizacionApi";
import { fetchMotivos, type CatalogItem } from "../../api/gridApi";
import { useAppFeedback } from "../../components/feedback";
import { TableExportBoxStyles, TableExportButtonStyles } from "../../styles/TablasStyle";
import { applyFormErrorsFromApi } from "../../utils/parseApiError";
import { AppButton, AppSelect, AppTextField, ExportDataDialog } from "../../ui";
import {
  matchesPlazoSlice,
  operativePlazoSlicePeerToInvalidate,
  operativePlazoSliceShouldFetch,
  sliceLabel,
  type PlazoOperativoSlice,
  type OperativePlazoExpedienteSlice,
} from "./gestionNotificacionPlazo";
import { normalizeNotificacionBandejaItems } from "./normalizeNotificacionBandejaItems";
import {
  dedupeNotificacionHistorialRows,
  notificacionHistorialRowKey,
} from "./dedupeNotificacionHistorialRows";
import { subscribeGestionNotificacionReinspeccionRefresh } from "./gestionNotificacionReinspeccionRefresh";
import { reinspeccionNotificacionBandejaRowKey } from "./gestionNotificacionReinspeccionRowKey";
import { mapPendienteReinspeccionNotificacionToGestionRow } from "./mapPendienteReinspeccionNotificacionToGestionRow";
import {
  NotificacionDetalleDocumentalDialog,
  type NotificacionDetalleModalVariant,
} from "./components/NotificacionDetalleDocumentalDialog";
import { ReinspeccionOperativaAccionCell } from "./components/ReinspeccionOperativaAccionCell";
import { OperRutaPoolAccionesCell } from "../../components/operRuta/OperRutaPoolAccionesCell";
import {
  estaBloqueadoParaGestionDocumental,
  MENSAJE_BLOQUEO_GESTION_POOL_RUTA,
} from "../../utils/operRutaPoolAcciones";
import {
  type GuardarProrrogaResult,
  prorrogaAltaSuccessMessage,
  volvioEnPlazoDesdeExpedienteMeta,
} from "./utils/prorrogaSuccessMessage";
import { exportNotificacionesDataset } from "./utils/exportNotificacionesDataset";
import {
  buildHistorialNotificacionFiltroPayload,
  fetchHistorialNotificacionConPayload,
  historialNotificacionHasSpecificSearch,
  type HistorialNotificacionFiltroPayload,
} from "./utils/buildHistorialNotificacionFiltroPayload";
import {
  buildOperativaNotificacionFiltroPayload,
  type OperativaNotificacionFiltroPayload,
} from "./utils/buildOperativaNotificacionFiltroPayload";
import { shouldResetOperativaFiltroOnTabChange } from "./utils/operativaNotificacionTabChange";
import { refreshNotificacionesPostProrroga } from "./utils/refreshNotificacionesPostProrroga";
import {
  clearPersistKeyIfMatch,
  GESTION_PERSIST_OPS,
  GESTION_RECONCILE_REFRESH_MSG,
  invalidatePendingMutationCallbacks,
  isMutationSeqCurrent,
  isPersistingForRow,
  nextMutationSeq,
  runGestionReconcile,
  type GestionPersistKey,
} from "../../utils/gestionMutationLifecycle";
import {
  notificacionEstadoOperativoChipColor,
} from "./utils/notificacionEstadoOperativo";
import { formatEstadoOperativoPoolLabel } from "../../utils/formatEstadoOperativoPoolLabel";
import { perfLog, perfTimed } from "../../utils/perfLog";

/** Operativas primero; `total` = Historial (documental), al final. */
const PLAZO_TAB_ORDER: PlazoOperativoSlice[] = ["en_plazo", "por_vencer", "vencidas_o_hoy", "total"];

/** Pestañas operativas para deep-link desde Actuación (excluye `total` / historial). */
const NOTIF_DEEPLINK_OPERATIVE_SLICES: PlazoOperativoSlice[] = ["en_plazo", "por_vencer", "vencidas_o_hoy"];

type HistPeriodMode = "month" | "range";

const MESES_OPTS = Array.from({ length: 12 }, (_, i) => ({
  value: String(i + 1),
  label: String(i + 1),
}));

const MESES_OPTS_WITH_EMPTY = [{ value: "", label: "—" }, ...MESES_OPTS];

function yearOptions(center: number): { value: string; label: string }[] {
  const out: { value: string; label: string }[] = [{ value: "", label: "—" }];
  for (let y = center - 5; y <= center + 2; y++) out.push({ value: String(y), label: String(y) });
  return out;
}

function contribuyenteText(row: IActuacionesPendientesItem): string {
  return contribuyenteBandejaLabel(row.contrib_apellido, row.contrib_nombre, row.razon_social);
}

function domicilioText(row: IActuacionesPendientesItem): string {
  const t = formatActuacionListDomicilioLinea(row).trim();
  return t || "—";
}

/** Fecha de actuación y orden de trabajo (misma idea que comprobación; dos renglones, sin chips). */
function notificacionFechaOtCelda(row: IActuacionesPendientesItem): { fecha: string; ot: string } {
  const fecha = (row.fecha_actuacion ?? "").toString().trim() || "—";
  const ot = (row.orden_trabajo_numero ?? "").toString().trim() || "—";
  return { fecha, ot };
}

function notificacionFechaOtSortKey(row: IActuacionesPendientesItem): string {
  const { fecha, ot } = notificacionFechaOtCelda(row);
  return `${fecha} ${ot}`;
}

function motivosNotif(row: IActuacionesPendientesItem): string {
  const parts = [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3].filter(
    (s): s is string => Boolean(s && String(s).trim())
  );
  return parts.join(", ") || "—";
}

function motivosSegments(row: IActuacionesPendientesItem): string[] {
  return [row.notificacion_motivo_1, row.notificacion_motivo_2, row.notificacion_motivo_3]
    .map((s) => (s ?? "").trim())
    .filter((s) => s.length > 0);
}

/** Días restantes + prórroga total en días (menos columnas, más panorama). */
function plazoResumenText(row: IActuacionesPendientesItem): string {
  const dPart =
    row.dias_restantes === null || row.dias_restantes === undefined
      ? "—"
      : row.dias_restantes === 1
        ? "1 día"
        : `${row.dias_restantes} días`;
  const prorrogaDias = row.notificacion_prorroga_dias;
  const pPart =
    prorrogaDias != null && prorrogaDias > 0
      ? prorrogaDias === 1
        ? "1 día prórroga"
        : `${prorrogaDias} días prórroga`
      : row.plazos_otorgados === null || row.plazos_otorgados === undefined
        ? "—"
        : row.plazos_otorgados === 0
          ? "sin prórroga"
          : row.plazos_otorgados === 1
            ? "1 prórroga"
            : `${row.plazos_otorgados} prórrogas`;
  if (dPart === "—" && pPart === "—") return "—";
  return `${dPart} · ${pPart}`;
}

function historialNotificacionRows(
  items: IActuacionesPendientesItem[],
  metaSourceType?: string | null
): IActuacionesPendientesItem[] {
  return dedupeNotificacionHistorialRows(normalizeNotificacionBandejaItems(items, metaSourceType));
}

function trimToNull(s: string): string | null {
  const t = s.trim();
  return t.length > 0 ? t : null;
}

type NotificacionBandejaTableProps = {
  rows: IActuacionesPendientesItem[];
  columns: MRT_ColumnDef<IActuacionesPendientesItem>[];
  toolbar?: () => React.ReactNode;
  /** Misma acotación de altura que Recorrido bajo panel documental (scroll del layout). */
  documentalListViewport?: boolean;
  getRowId?: (row: IActuacionesPendientesItem) => string;
  pagination?: MRT_PaginationState;
  onPaginationChange?: (updater: MRT_Updater<MRT_PaginationState>) => void;
  manualPagination?: boolean;
  rowCount?: number;
};

/** Tabla MRT reutilizable (operativa vs historial). */
function NotificacionBandejaTable({
  rows,
  columns,
  toolbar,
  documentalListViewport,
  getRowId,
  pagination,
  onPaginationChange,
  manualPagination,
  rowCount,
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

  const table = useMaterialReactTable(
    {
      ...DARK_TABLE_CONFIG,
      ...MRT_READ_ONLY_BANDEJA,
      ...documentalMrtLayout,
      ...BANDEJA_MRT_BODY_CELL_PROPS,
      columns,
      data: rows,
      density: "compact",
      enableColumnFilters: false,
      enableGlobalFilter: false,
      ...(getRowId ? { getRowId: (row) => getRowId(row) } : {}),
      ...(manualPagination ? { manualPagination: true, rowCount: rowCount ?? 0 } : {}),
      renderTopToolbarCustomActions: toolbar,
      state: {
        ...BANDEJA_MRT_SPINNER_LOADING_STATE,
        ...(pagination ? { pagination } : {}),
      },
      ...(onPaginationChange ? { onPaginationChange } : {}),
    } as MRT_TableOptions<IActuacionesPendientesItem>
  );
  return <MaterialReactTable table={table} />;
}

/**
 * Bandeja: operativa con GET omitir_rango_fecha; historial con mes/año tras aplicar filtro.
 */
const GestionNotificacionPage = () => {
  const feedback = useAppFeedback();
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const [searchParams, setSearchParams] = useSearchParams();
  const notifDeepLinkProcessedKey = useRef<string | null>(null);
  const [notificacionDeepLinkAviso, setNotificacionDeepLinkAviso] = useState<string | null>(null);
  const defaultMonthYear = useMemo(() => {
    const d = new Date(`${defaultRange.desde}T12:00:00`);
    return { mes: d.getMonth() + 1, anio: d.getFullYear() };
  }, [defaultRange.desde]);

  const [items, setItems] = useState<IActuacionesPendientesItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reinspeccionItems, setReinspeccionItems] = useState<IActuacionesPendientesItem[]>([]);
  const [reinspeccionLoading, setReinspeccionLoading] = useState(false);
  const [reinspeccionError, setReinspeccionError] = useState<string | null>(null);
  const [plazoSlice, setPlazoSlice] = useState<PlazoOperativoSlice>("en_plazo");

  const [histPeriodMode, setHistPeriodMode] = useState<HistPeriodMode>("month");
  const [histMes, setHistMes] = useState<number | "">("");
  const [histAnio, setHistAnio] = useState<number | "">("");
  const [histDesde, setHistDesde] = useState<string | null>(null);
  const [histHasta, setHistHasta] = useState<string | null>(null);
  const [histCombinarConPeriodo, setHistCombinarConPeriodo] = useState(false);
  const [histDistritoId, setHistDistritoId] = useState<number | "">("");
  const [histContribQ, setHistContribQ] = useState("");
  const [histCalleQ, setHistCalleQ] = useState("");
  const [histNumNotif, setHistNumNotif] = useState("");
  const [histMotivoId, setHistMotivoId] = useState<number | "">("");
  const [opDesde, setOpDesde] = useState<string | null>(null);
  const [opHasta, setOpHasta] = useState<string | null>(null);
  const [opNumNotif, setOpNumNotif] = useState("");
  const [opCalleQ, setOpCalleQ] = useState("");
  const [opApplied, setOpApplied] = useState<OperativaNotificacionFiltroPayload | null>(null);
  const opAppliedRef = useRef<OperativaNotificacionFiltroPayload | null>(null);
  const [distritosHistorial, setDistritosHistorial] = useState<DistritoCatalogoItem[]>([]);
  const [motivosHistorial, setMotivosHistorial] = useState<CatalogItem[]>([]);
  const [historialFiltroAplicado, setHistorialFiltroAplicado] = useState(false);
  const [historialRows, setHistorialRows] = useState<IActuacionesPendientesItem[]>([]);
  const [historialLoading, setHistorialLoading] = useState(false);
  const [historialError, setHistorialError] = useState<string | null>(null);
  const [historialMeta, setHistorialMeta] = useState<{
    total: number;
    desde: string | null;
    hasta: string | null;
    page?: number;
    page_size?: number;
    pages?: number;
  } | null>(null);
  const [historialApplied, setHistorialApplied] = useState<HistorialNotificacionFiltroPayload | null>(null);
  const [historialPagination, setHistorialPagination] = useState<MRT_PaginationState>({
    pageIndex: 0,
    pageSize: DEFAULT_BANDEJA_CLIENT_PAGE_SIZE,
  });

  const distritoSelectOptionsHistorial = useMemo(
    () => [
      { value: "", label: "Todos los distritos" },
      ...distritosHistorial.map((d) => ({ value: String(d.id), label: d.nombre })),
    ],
    [distritosHistorial]
  );

  const motivoSelectOptionsHistorial = useMemo(
    () => [
      { value: "", label: "Todos los motivos" },
      ...motivosHistorial.map((m) => ({ value: String(m.id), label: m.nombre })),
    ],
    [motivosHistorial]
  );

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [distritosRes, motivosRes] = await Promise.all([
          fetchDistritosCatalogo(),
          fetchMotivos(),
        ]);
        if (!cancelled) {
          setDistritosHistorial(distritosRes.items ?? []);
          setMotivosHistorial(motivosRes.items ?? []);
        }
      } catch {
        if (!cancelled) {
          setDistritosHistorial([]);
          setMotivosHistorial([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const prevPlazoSliceRef = useRef<PlazoOperativoSlice>(plazoSlice);
  const plazoSliceRef = useRef<PlazoOperativoSlice>(plazoSlice);
  const operativeSliceLoadedRef = useRef<Record<OperativePlazoExpedienteSlice, boolean>>({
    en_plazo: false,
    por_vencer: false,
  });
  const [itemsBySlice, setItemsBySlice] = useState<
    Record<OperativePlazoExpedienteSlice, IActuacionesPendientesItem[]>
  >({
    en_plazo: [],
    por_vencer: [],
  });
  const itemsBySliceRef = useRef(itemsBySlice);
  itemsBySliceRef.current = itemsBySlice;
  const reinspeccionDataLoadedRef = useRef(false);

  const invalidateOtherOperativeSlices = useCallback((active: OperativePlazoExpedienteSlice) => {
    const other = operativePlazoSlicePeerToInvalidate(active);
    operativeSliceLoadedRef.current[other] = false;
  }, []);

  useEffect(() => {
    opAppliedRef.current = opApplied;
  }, [opApplied]);

  const invalidateOperativeSlices = useCallback(() => {
    operativeSliceLoadedRef.current.en_plazo = false;
    operativeSliceLoadedRef.current.por_vencer = false;
    reinspeccionDataLoadedRef.current = false;
  }, []);

  const loadPlazoSliceData = useCallback(
    async (
      slice: OperativePlazoExpedienteSlice,
      force = false,
      filters: OperativaNotificacionFiltroPayload | null = opAppliedRef.current,
      opts?: { silent?: boolean }
    ) => {
      if (!operativePlazoSliceShouldFetch(slice, operativeSliceLoadedRef.current, force)) {
        perfLog("notificaciones.tab.cacheHit", { slice });
        if (plazoSliceRef.current === slice) {
          setItems(itemsBySliceRef.current[slice]);
        }
        return;
      }
      if (!opts?.silent) setLoading(true);
      setError(null);
      const hasDateRange = Boolean(filters?.desde || filters?.hasta);
      try {
        const resp = await perfTimed(
          "notificaciones.loadPlazoSlice",
          () =>
            getActuacionesPendientesExpediente(filters?.desde ?? null, filters?.hasta ?? null, "notificacion", null, {
              omitirRangoFecha: !hasDateRange,
              plazoSlice: slice,
              numeroNotificacion: filters?.numeroNotificacion ?? null,
              calleQ: filters?.calleQ ?? null,
            }),
          (r) => ({ slice, rows: r.items.length, total: r.meta.total })
        );
        const normalized = normalizeNotificacionBandejaItems(resp.items, resp.meta.source_type);
        setItemsBySlice((prev) => ({ ...prev, [slice]: normalized }));
        operativeSliceLoadedRef.current[slice] = true;
        if (plazoSliceRef.current === slice) {
          setItems(normalized);
        }
        perfLog("notificaciones.loadPlazoSlice.state", { slice, items: normalized.length });
      } catch (err: unknown) {
        const detail =
          err && typeof err === "object" && "response" in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : null;
        setError(detail || "Error al cargar la bandeja");
        if (plazoSliceRef.current === slice) {
          setItems([]);
        }
      } finally {
        if (!opts?.silent) setLoading(false);
      }
    },
    []
  );

  const [selected, setSelected] = useState<IActuacionesPendientesItem | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalEsReinspeccionNotificacion, setModalEsReinspeccionNotificacion] = useState(false);
  const [modalVariant, setModalVariant] = useState<NotificacionDetalleModalVariant>("documental");
  const [expNumero, setExpNumero] = useState("");
  const [expFecha, setExpFecha] = useState("");
  const [prorrogaDias, setProrrogaDias] = useState("0");
  const [persistKey, setPersistKey] = useState<GestionPersistKey | null>(null);
  const mutationSeqRef = useRef(0);
  const selectedRef = useRef<IActuacionesPendientesItem | null>(null);
  const historialFiltroAplicadoRef = useRef(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [modalApiError, setModalApiError] = useState<string | null>(null);

  useEffect(() => {
    selectedRef.current = selected;
  }, [selected]);

  useEffect(() => {
    historialFiltroAplicadoRef.current = historialFiltroAplicado;
  }, [historialFiltroAplicado]);

  const modalAltaExpedientePersisting = isPersistingForRow(
    persistKey,
    selected?.id,
    GESTION_PERSIST_OPS.notifAltaExpediente
  );

  const [syncLoading, setSyncLoading] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState<
    | null
    | { kind: "success"; metrics: ISyncNotificacionesVencidasResponse }
    | { kind: "error"; message: string }
  >(null);

  const [exportOpen, setExportOpen] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const loadPendientesReinspeccionNotificacion = useCallback(
    async (
      filters: OperativaNotificacionFiltroPayload | null = opAppliedRef.current,
      opts?: { silent?: boolean }
    ) => {
      if (!opts?.silent) setReinspeccionLoading(true);
      setReinspeccionError(null);
      try {
        const rows = await perfTimed(
          "notificaciones.loadPendientesReinspeccion",
          () =>
            getPendientesReinspeccionNotificacion({
              desde: filters?.desde ?? null,
              hasta: filters?.hasta ?? null,
              numeroNotificacion: filters?.numeroNotificacion ?? null,
              calleQ: filters?.calleQ ?? null,
            }),
          (r) => ({ rows: r.length })
        );
        setReinspeccionItems(
          normalizeNotificacionBandejaItems(rows, "notificacion").map(mapPendienteReinspeccionNotificacionToGestionRow)
        );
        reinspeccionDataLoadedRef.current = true;
      } catch (err: unknown) {
        const detail =
          err && typeof err === "object" && "response" in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : null;
        setReinspeccionError(detail || "Error al cargar pendientes de reinspección");
        setReinspeccionItems([]);
      } finally {
        if (!opts?.silent) setReinspeccionLoading(false);
      }
    },
    []
  );

  const handleApplyOperativaFiltro = useCallback(() => {
    const payload = buildOperativaNotificacionFiltroPayload({
      desde: opDesde,
      hasta: opHasta,
      numeroNotificacion: opNumNotif,
      calleQ: opCalleQ,
    });
    setOpApplied(payload);
    opAppliedRef.current = payload;
    const active = plazoSliceRef.current;
    if (active === "en_plazo" || active === "por_vencer") {
      void loadPlazoSliceData(active, true, payload);
    } else if (active === "vencidas_o_hoy") {
      void loadPendientesReinspeccionNotificacion(payload);
    }
  }, [
    opDesde,
    opHasta,
    opNumNotif,
    opCalleQ,
    loadPlazoSliceData,
    loadPendientesReinspeccionNotificacion,
  ]);

  const handleClearOperativaFiltro = useCallback(() => {
    setOpDesde(null);
    setOpHasta(null);
    setOpNumNotif("");
    setOpCalleQ("");
    setOpApplied(null);
    opAppliedRef.current = null;
    const active = plazoSliceRef.current;
    if (active === "en_plazo" || active === "por_vencer") {
      void loadPlazoSliceData(active, true, null);
    } else if (active === "vencidas_o_hoy") {
      void loadPendientesReinspeccionNotificacion(null);
    }
  }, [loadPlazoSliceData, loadPendientesReinspeccionNotificacion]);

  useEffect(() => {
    const prev = prevPlazoSliceRef.current;
    const tabChanged = plazoSlice !== prev;

    if (tabChanged) {
      if (shouldResetOperativaFiltroOnTabChange(prev, plazoSlice)) {
        setOpNumNotif("");
        setOpCalleQ("");
        setOpApplied(null);
        opAppliedRef.current = null;
      }
      if (plazoSlice === "total" && prev !== "total") {
        setHistorialFiltroAplicado(false);
        setHistorialRows([]);
        setHistorialError(null);
        setHistorialApplied(null);
        setHistorialMeta(null);
        setHistorialPagination((prevPagination) => resetClientPaginationPageIndex(prevPagination));
      }
      prevPlazoSliceRef.current = plazoSlice;
    }

    plazoSliceRef.current = plazoSlice;

    if (plazoSlice === "en_plazo" || plazoSlice === "por_vencer") {
      perfLog("notificaciones.tab.fetch", { slice: plazoSlice, tabChanged });
      const filters = tabChanged ? null : opAppliedRef.current;
      void loadPlazoSliceData(plazoSlice, tabChanged, filters);
    } else if (plazoSlice === "vencidas_o_hoy") {
      if (tabChanged || !reinspeccionDataLoadedRef.current) {
        perfLog("notificaciones.tab.lazy", { slice: plazoSlice, tabChanged });
        void loadPendientesReinspeccionNotificacion(tabChanged ? null : opAppliedRef.current).then(() => {
          reinspeccionDataLoadedRef.current = true;
        });
      } else {
        perfLog("notificaciones.tab.cacheHit", { slice: plazoSlice });
      }
    }
  }, [plazoSlice, loadPlazoSliceData, loadPendientesReinspeccionNotificacion]);

  useEffect(() => {
    return subscribeGestionNotificacionReinspeccionRefresh(() => {
      reinspeccionDataLoadedRef.current = false;
      if (plazoSliceRef.current === "vencidas_o_hoy") {
        void loadPendientesReinspeccionNotificacion().then(() => {
          reinspeccionDataLoadedRef.current = true;
        });
      }
    });
  }, [loadPendientesReinspeccionNotificacion]);

  const loadHistorialDesdeFiltro = useCallback(() => {
    const built = buildHistorialNotificacionFiltroPayload(
      {
      periodMode: histPeriodMode,
      mes: histMes,
      anio: histAnio,
      desde: histDesde,
      hasta: histHasta,
      distritoId: histDistritoId,
      numeroNotificacion: histNumNotif,
      calleQ: histCalleQ,
      contribuyenteQ: histContribQ,
      motivoId: histMotivoId,
      combinarConPeriodo: histCombinarConPeriodo,
      },
      motivosHistorial
    );
    if (!built.ok) {
      setHistorialError(built.error);
      return;
    }

    setHistorialError(null);
    setHistorialApplied(built.payload);
    setHistorialFiltroAplicado(true);
    setHistorialPagination((prev) => resetClientPaginationPageIndex(prev));
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
    histMotivoId,
    histCombinarConPeriodo,
    motivosHistorial,
  ]);

  useEffect(() => {
    if (!historialFiltroAplicado || !historialApplied) return;

    let cancelled = false;
    setHistorialLoading(true);
    setHistorialError(null);

    void perfTimed(
      "notificaciones.loadHistorial",
      () =>
        fetchHistorialNotificacionConPayload(historialApplied, {
          page: historialPagination.pageIndex + 1,
          pageSize: historialPagination.pageSize,
        }),
      (r) => ({ rows: r.items.length, total: r.meta.total, page: r.meta.page })
    )
      .then((resp) => {
        if (cancelled) return;
        setHistorialRows(historialNotificacionRows(resp.items, resp.meta.source_type));
        setHistorialMeta({
          total: resp.meta.total,
          desde: resp.meta.desde,
          hasta: resp.meta.hasta,
          page: resp.meta.page,
          page_size: resp.meta.page_size,
          pages: resp.meta.pages,
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const detail =
          err && typeof err === "object" && "response" in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : null;
        setHistorialError(detail || "Error al cargar el historial");
        setHistorialRows([]);
        setHistorialFiltroAplicado(false);
        setHistorialApplied(null);
        setHistorialMeta(null);
      })
      .finally(() => {
        if (!cancelled) setHistorialLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [
    historialFiltroAplicado,
    historialApplied,
    historialPagination.pageIndex,
    historialPagination.pageSize,
  ]);

  const recargarHistorialSiAplica = useCallback(async () => {
    if (!historialFiltroAplicado || !historialApplied) return;
    setHistorialLoading(true);
    setHistorialError(null);
    try {
      const resp = await fetchHistorialNotificacionConPayload(historialApplied, {
        page: historialPagination.pageIndex + 1,
        pageSize: historialPagination.pageSize,
      });
      setHistorialRows(historialNotificacionRows(resp.items, resp.meta.source_type));
      setHistorialMeta({
        total: resp.meta.total,
        desde: resp.meta.desde,
        hasta: resp.meta.hasta,
        page: resp.meta.page,
        page_size: resp.meta.page_size,
        pages: resp.meta.pages,
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
  }, [
    historialFiltroAplicado,
    historialApplied,
    historialPagination.pageIndex,
    historialPagination.pageSize,
  ]);

  const handleSyncNotificacionesVencidas = useCallback(async () => {
    setSyncLoading(true);
    setSyncFeedback(null);
    try {
      const metrics = await postSyncNotificacionesVencidas();
      setSyncFeedback({ kind: "success", metrics });
      operativeSliceLoadedRef.current.en_plazo = false;
      operativeSliceLoadedRef.current.por_vencer = false;
      const active = plazoSliceRef.current;
      if (active === "en_plazo" || active === "por_vencer") {
        await loadPlazoSliceData(active, true);
      }
      if (reinspeccionDataLoadedRef.current || active === "vencidas_o_hoy") {
        reinspeccionDataLoadedRef.current = false;
        if (active === "vencidas_o_hoy") {
          await loadPendientesReinspeccionNotificacion();
          reinspeccionDataLoadedRef.current = true;
        }
      }
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
  }, [loadPlazoSliceData, loadPendientesReinspeccionNotificacion, historialFiltroAplicado, recargarHistorialSiAplica]);

  const notificacionRows = useMemo(
    () => items.filter((r) => r.source_type === "NOTIFICACION"),
    [items]
  );

  const sliceCounts = useMemo(
    () => ({
      en_plazo: itemsBySlice.en_plazo.length,
      por_vencer: itemsBySlice.por_vencer.length,
      vencidas_o_hoy: reinspeccionItems.length,
      total: historialMeta?.total ?? (historialFiltroAplicado ? historialRows.length : 0),
    }),
    [
      itemsBySlice.en_plazo.length,
      itemsBySlice.por_vencer.length,
      reinspeccionItems.length,
      historialMeta?.total,
      historialFiltroAplicado,
      historialRows.length,
    ]
  );

  const esTabReinspeccionOperativa = plazoSlice === "vencidas_o_hoy";

  const filteredRowsOperativa = useMemo(() => {
    if (esTabReinspeccionOperativa) return reinspeccionItems;
    return notificacionRows.filter((r) => matchesPlazoSlice(r, plazoSlice));
  }, [notificacionRows, plazoSlice, reinspeccionItems, esTabReinspeccionOperativa]);

  useEffect(() => {
    if (plazoSlice === "total") return;
    perfLog("notificaciones.clientFilter", {
      slice: plazoSlice,
      sourceRows: notificacionRows.length,
      visibleRows: filteredRowsOperativa.length,
    });
  }, [plazoSlice, notificacionRows.length, filteredRowsOperativa.length]);

  const operativaLoading = esTabReinspeccionOperativa ? reinspeccionLoading : loading;
  const operativaError = esTabReinspeccionOperativa ? reinspeccionError : error;

  const openModal = useCallback(
    (
      row: IActuacionesPendientesItem,
      variant: NotificacionDetalleModalVariant,
      opts?: { reinspeccion?: boolean }
    ) => {
    invalidatePendingMutationCallbacks(mutationSeqRef);
    setPersistKey(null);
    setModalVariant(variant);
    setModalEsReinspeccionNotificacion(Boolean(opts?.reinspeccion));
    setSelected(row);
    setExpNumero("");
    setExpFecha("");
    setProrrogaDias("0");
    setFieldErrors({});
    setModalApiError(null);
    setModalOpen(true);
  }, []);

  useEffect(() => {
    const raw = searchParams.get("actuacionId");
    if (!raw) {
      notifDeepLinkProcessedKey.current = null;
      setNotificacionDeepLinkAviso(null);
      return;
    }
    if (loading && reinspeccionLoading) return;

    const key = `notif-focus:${raw}`;
    if (notifDeepLinkProcessedKey.current === key) return;

    const aid = Number.parseInt(raw, 10);
    if (!Number.isFinite(aid)) return;

    const rowPlazo =
      itemsBySlice.en_plazo.find((r) => r.id === aid && r.source_type === "NOTIFICACION") ??
      itemsBySlice.por_vencer.find((r) => r.id === aid && r.source_type === "NOTIFICACION") ??
      items.find((r) => r.id === aid && r.source_type === "NOTIFICACION");
    const rowRein = reinspeccionItems.find((r) => r.id === aid);
    const row = rowRein ?? rowPlazo;
    const clearParam = () => {
      notifDeepLinkProcessedKey.current = key;
      const next = new URLSearchParams(searchParams);
      next.delete("actuacionId");
      setSearchParams(next, { replace: true });
    };

    if (!row) {
      setNotificacionDeepLinkAviso(
        `No encontramos la actuación n.º ${aid} en la bandeja operativa de notificaciones (revisá pestañas de plazo o recargá la lista).`
      );
      clearParam();
      return;
    }

    if (rowRein) {
      setPlazoSlice("vencidas_o_hoy");
      setNotificacionDeepLinkAviso(null);
      openModal(rowRein, "documental", { reinspeccion: true });
      clearParam();
      return;
    }

    const sliceHit = NOTIF_DEEPLINK_OPERATIVE_SLICES.find((s) => matchesPlazoSlice(row, s));
    if (sliceHit) {
      setPlazoSlice(sliceHit);
      setNotificacionDeepLinkAviso(null);
      const variant: NotificacionDetalleModalVariant =
        row.notificacion_editable === false ? "documental" : "soloExpediente";
      openModal(row, variant);
      clearParam();
      return;
    }

    setNotificacionDeepLinkAviso(
      `Actuación n.º ${aid}: el plazo no coincide con ninguna pestaña operativa actual (revisá «Historial de notificaciones» por período). OT ${(row.orden_trabajo_numero ?? "").trim() || "—"}.`
    );
    clearParam();
  }, [loading, reinspeccionLoading, items, itemsBySlice, reinspeccionItems, searchParams, setSearchParams, openModal]);

  const dismissModal = useCallback(() => {
    setModalOpen(false);
    setSelected(null);
    setFieldErrors({});
    setModalApiError(null);
  }, []);

  const closeModal = () => {
    if (modalAltaExpedientePersisting) return;
    dismissModal();
  };

  const reconcileBandejasSilent = useCallback(() => {
    runGestionReconcile(
      async () => {
        if (plazoSliceRef.current === "total") {
          if (historialFiltroAplicadoRef.current) {
            await recargarHistorialSiAplica();
          }
          return;
        }
        await refreshNotificacionesPostProrroga({
          filters: opAppliedRef.current,
          activeSlice: plazoSliceRef.current,
          invalidateOperativeSlices,
          loadPlazoSlice: (slice, force, filters) =>
            loadPlazoSliceData(slice, force, filters, { silent: true }),
          loadReinspeccion: (filters) => loadPendientesReinspeccionNotificacion(filters, { silent: true }),
        });
      },
      () => {
        feedback.error(GESTION_RECONCILE_REFRESH_MSG);
      }
    );
  }, [
    feedback,
    invalidateOperativeSlices,
    loadPlazoSliceData,
    loadPendientesReinspeccionNotificacion,
    recargarHistorialSiAplica,
  ]);

  const handleExpedienteMutacionExitosa = useCallback(
    (mensaje: string) => {
      const actuacionId = selectedRef.current?.id ?? null;
      const seq = mutationSeqRef.current;
      perfLog("notificaciones.modal.mutacion.refetch", { mensaje, slice: plazoSlice });
      feedback.success(mensaje);
      if (
        actuacionId != null &&
        selectedRef.current?.id === actuacionId &&
        isMutationSeqCurrent(mutationSeqRef, seq)
      ) {
        dismissModal();
      }
      reconcileBandejasSilent();
    },
    [feedback, plazoSlice, dismissModal, reconcileBandejasSilent]
  );

  const handleSave = useCallback(async (): Promise<GuardarProrrogaResult> => {
    if (!selected) return { ok: false };
    const actuacionId = selected.id;
    const next: Record<string, string> = {};
    if (!expNumero.trim()) next.expNumero = "Completá el número de expediente.";
    if (!expFecha) next.expFecha = "Completá la fecha de expediente.";
    const pr = Number(prorrogaDias);
    if (prorrogaDias.trim() !== "" && (Number.isNaN(pr) || pr < 0)) {
      next.prorrogaDias = "Indicá un número de días válido (0 o más).";
    }
    setFieldErrors(next);
    if (Object.keys(next).length > 0) return { ok: false };

    const seq = nextMutationSeq(mutationSeqRef);
    setPersistKey({ actuacionId, op: GESTION_PERSIST_OPS.notifAltaExpediente });
    setModalApiError(null);
    try {
      const payload: ICreateExpedienteRequest = {
        expediente_numero: expNumero.trim(),
        fecha_expediente: expFecha,
        source_type: "NOTIFICACION",
        prorroga_dias: Number(prorrogaDias) || 0,
      };
      const resp = await createExpedienteDesdeActuacion(actuacionId, payload);
      if (!isMutationSeqCurrent(mutationSeqRef, seq)) {
        return { ok: false };
      }

      if (selectedRef.current?.id === actuacionId) {
        setExpNumero("");
        setExpFecha("");
        setProrrogaDias("0");
        setFieldErrors({});
      }

      setPersistKey((prev) => clearPersistKeyIfMatch(prev, actuacionId, GESTION_PERSIST_OPS.notifAltaExpediente));

      const volvioEnPlazo = volvioEnPlazoDesdeExpedienteMeta(resp.meta?.next_state_hint);
      feedback.success(prorrogaAltaSuccessMessage(volvioEnPlazo));

      if (selectedRef.current?.id === actuacionId && isMutationSeqCurrent(mutationSeqRef, seq)) {
        dismissModal();
      }

      reconcileBandejasSilent();
      return { ok: true, volvioEnPlazo };
    } catch (err: unknown) {
      if (!isMutationSeqCurrent(mutationSeqRef, seq)) {
        return { ok: false };
      }
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setModalApiError(detail || "No se pudo añadir el expediente de plazo");
      return { ok: false };
    } finally {
      if (isMutationSeqCurrent(mutationSeqRef, seq)) {
        setPersistKey((prev) => clearPersistKeyIfMatch(prev, actuacionId, GESTION_PERSIST_OPS.notifAltaExpediente));
      }
    }
  }, [selected, expNumero, expFecha, prorrogaDias, feedback, dismissModal, reconcileBandejasSilent]);

  /** Anchos reducidos para dar lugar a la columna Acción (MRT sin resize en bandeja). */
  const columnsDataCompact = useMemo<MRT_ColumnDef<IActuacionesPendientesItem>[]>(
    () => [
      {
        id: "fecha_ot",
        header: "Fecha · OT",
        size: 118,
        accessorFn: (row) => notificacionFechaOtSortKey(row),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => {
          const { fecha, ot } = notificacionFechaOtCelda(row.original);
          return <BandejaFechaYChipOtCell fecha={fecha} ot={ot === "—" ? "" : ot} />;
        },
      },
      {
        id: "contribuyente",
        header: "Contribuyente",
        size: 156,
        accessorFn: (row) => contribuyenteText(row),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => <BandejaEllipsisCell value={contribuyenteText(row.original)} />,
      },
      {
        id: "domicilio",
        header: "Domicilio",
        size: 132,
        accessorFn: (row) => domicilioText(row),
        Cell: ({ row }) => <BandejaEllipsisCell value={domicilioText(row.original)} />,
      },
      {
        id: "acta_notificacion",
        header: "Nº notif.",
        size: 96,
        accessorFn: (row) => row.acta_notificacion_num ?? "—",
        Cell: ({ row }) => {
          const n = (row.original.acta_notificacion_num ?? "").trim();
          return <BandejaActaChipCell label={n ? `Notif. ${n}` : "—"} />;
        },
      },
      {
        id: "motivos",
        header: "Motivo(s)",
        size: 112,
        accessorFn: (row) => motivosNotif(row),
        Cell: ({ row }) => <BandejaSegmentChipsCell segments={motivosSegments(row.original)} />,
      },
      {
        id: "plazo_resumen",
        header: "Plazo",
        size: 100,
        accessorFn: (row) => plazoResumenText(row),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => (
          <BandejaSegmentChipsCell segments={splitMiddleDot(plazoResumenText(row.original))} />
        ),
      },
      {
        id: "estado_operativo",
        header: "Estado operativo",
        size: 132,
        accessorFn: (row) => formatEstadoOperativoPoolLabel(row),
        Cell: ({ row }) => {
          const label = formatEstadoOperativoPoolLabel(row.original);
          if (label === "—") return <BandejaEllipsisCell value="—" />;
          return (
            <Chip
              size="small"
              label={label}
              color={notificacionEstadoOperativoChipColor(row.original.estado_operativo_pool)}
              variant="outlined"
              sx={{ maxWidth: "100%" }}
            />
          );
        },
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
        size: 168,
        grow: false,
        enableResizing: false,
        Cell: ({ row }) => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModal(row.original, "soloExpediente")}>
            Prórrogas
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
        size: 118,
        grow: false,
        enableResizing: false,
        Cell: ({ row }) => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModal(row.original, "documental")}>
            Ver detalle
          </AppButton>
        ),
      },
    ],
    [columnsDataCompact, openModal]
  );

  const columnsReinspeccionOperativa = useMemo<MRT_ColumnDef<IActuacionesPendientesItem>[]>(
    () => [
      ...columnsDataCompact,
      {
        id: "acciones",
        header: "Acción",
        size: 248,
        grow: false,
        enableResizing: false,
        Cell: ({ row }) => {
          const bloqueado = estaBloqueadoParaGestionDocumental(row.original);
          return (
          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap alignItems="center">
            <OperRutaPoolAccionesCell
              row={row.original}
              onRefresh={async (opts) => {
                await loadPendientesReinspeccionNotificacion(opAppliedRef.current, opts);
                reinspeccionDataLoadedRef.current = true;
              }}
              onSuccess={(msg) => feedback.success(msg)}
              onError={(msg) => feedback.error(msg)}
            />
            <ReinspeccionOperativaAccionCell
              disabled={bloqueado}
              disabledReason={bloqueado ? MENSAJE_BLOQUEO_GESTION_POOL_RUTA : undefined}
              onProrroga={() => openModal(row.original, "soloExpediente", { reinspeccion: true })}
            />
          </Stack>
          );
        },
      },
    ],
    [columnsDataCompact, openModal, loadPendientesReinspeccionNotificacion, feedback]
  );

  const refreshOperativaActiva = useCallback(async () => {
    if (esTabReinspeccionOperativa) {
      await loadPendientesReinspeccionNotificacion();
      reinspeccionDataLoadedRef.current = true;
      return;
    }
    if (plazoSlice === "en_plazo" || plazoSlice === "por_vencer") {
      invalidateOtherOperativeSlices(plazoSlice);
      await loadPlazoSliceData(plazoSlice, true);
    }
  }, [
    esTabReinspeccionOperativa,
    plazoSlice,
    loadPendientesReinspeccionNotificacion,
    loadPlazoSliceData,
    invalidateOtherOperativeSlices,
  ]);

  const renderOperativaToolbarRefresh = useCallback(
    () => (
      <Tooltip title="Actualizar listados">
        <span>
          <IconButton
            type="button"
            size="small"
            aria-label="Actualizar listados"
            disabled={operativaLoading}
            onClick={() => void refreshOperativaActiva()}
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
    [operativaLoading, refreshOperativaActiva]
  );

  const renderHistorialToolbarRefresh = useCallback(
    () => (
      <Tooltip title="Actualizar listados">
        <span>
          <IconButton
            type="button"
            size="small"
            aria-label="Actualizar listados"
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

  const tabSuffixOperativa = useCallback(
    (slice: Exclude<PlazoOperativoSlice, "total">): string => {
      if (slice === "vencidas_o_hoy") {
        if (reinspeccionLoading) return "…";
        return String(reinspeccionItems.length);
      }
      if (loading) return "…";
      return String(sliceCounts[slice]);
    },
    [loading, reinspeccionLoading, reinspeccionItems.length, sliceCounts]
  );

  const mostrarTablaOperativa = plazoSlice !== "total";
  const mostrarHistorial = plazoSlice === "total";

  const historialPaginationSummary = useMemo(
    () =>
      buildClientPaginationSummary({
        pageIndex: historialPagination.pageIndex,
        pageSize: historialPagination.pageSize,
        totalRows: historialMeta?.total ?? historialRows.length,
      }),
    [
      historialPagination.pageIndex,
      historialPagination.pageSize,
      historialMeta?.total,
      historialRows.length,
    ]
  );

  const handleExportNotificaciones = useCallback(
    async (options: {
      format: "excel" | "pdf";
      periodMode: "workweek" | "month" | "custom";
      desde: string;
      hasta: string;
    }) => {
      setExportLoading(true);
      setExportError(null);
      try {
        await exportNotificacionesDataset({
          format: options.format,
          desde: options.desde,
          hasta: options.hasta,
          plazoSlice,
          historialAppliedPayload:
            plazoSlice === "total" && historialFiltroAplicado && historialApplied
              ? historialApplied
              : null,
        });
        feedback.success("Exportación generada");
        setExportOpen(false);
      } catch (err: unknown) {
        const parsed = applyFormErrorsFromApi(err, {
          fallbackMessage: "No se pudo completar la exportación.",
        });
        setExportError(parsed.globalMessage ?? parsed.fieldErrors._global ?? "No se pudo completar la exportación.");
      } finally {
        setExportLoading(false);
      }
    },
    [feedback, historialApplied, historialFiltroAplicado, plazoSlice]
  );

  return (
    <Box sx={{ ...functionalPageShellSx, ...moduleContentColumnSx } as SxProps<Theme>}>
      {notificacionDeepLinkAviso ? (
        <Alert severity="info" sx={{ ...alertBaseStyles, mb: 1.5 }} onClose={() => setNotificacionDeepLinkAviso(null)}>
          {notificacionDeepLinkAviso}
        </Alert>
      ) : null}

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

      <Paper
        elevation={0}
        sx={{
          ...moduleSlicesPanelPaperSx,
          flexDirection: { xs: "column", sm: "row" },
          alignItems: { xs: "stretch", sm: "center" },
          gap: { xs: 1.25, sm: 1 },
        }}
      >
        <Tabs
          value={plazoSlice}
          onChange={(_, v) => setPlazoSlice(v as PlazoOperativoSlice)}
          variant="scrollable"
          allowScrollButtonsMobile
          sx={{ ...moduleSlicesTabsSx, flex: 1, minWidth: 0 }}
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
        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column", sm: "row" },
            alignItems: { xs: "stretch", sm: "center" },
            gap: { xs: 0.75, sm: 0.5 },
            flexShrink: 0,
            mb: { xs: 0.25, sm: 0 },
          }}
        >
          {plazoSlice !== "vencidas_o_hoy" && (
            <Box sx={{ ...TableExportBoxStyles, p: 0, flexDirection: "row" }}>
              <Button
                onClick={() => {
                  setExportError(null);
                  setExportOpen(true);
                }}
                startIcon={<FileDownloadOutlinedIcon />}
                sx={TableExportButtonStyles}
                disabled={exportLoading}
              >
                Exportar datos
              </Button>
            </Box>
          )}
          <AppButton
            dsVariant="primary"
            dsSize="sm"
            onClick={() => void handleSyncNotificacionesVencidas()}
            disabled={syncLoading || loading || reinspeccionLoading}
            sx={{
              alignSelf: { xs: "stretch", sm: "center" },
              fontFamily: '"Tactic Sans", sans-serif',
              fontWeight: 600,
              whiteSpace: { xs: "normal", sm: "nowrap" },
            }}
          >
            {syncLoading ? "Sincronizando…" : "Sincronizar vencimientos"}
          </AppButton>
        </Box>
      </Paper>

      {operativaError && (
        <Alert severity="error" sx={alertBaseStyles}>
          {operativaError}
        </Alert>
      )}

      {mostrarTablaOperativa && (
        <Box sx={filtroContainerStyles}>
          <Typography sx={filtroTitleStyles}>Filtros operativos</Typography>
          <Box sx={filtroGridStyles}>
            <Box sx={filtroItemStyles}>
              <AppTextField
                appearance="dense"
                fullWidth
                label="Desde"
                type="date"
                InputLabelProps={{ shrink: true }}
                value={opDesde ?? ""}
                onChange={(e) => setOpDesde(trimToNull(e.target.value))}
                variant="outlined"
              />
            </Box>
            <Box sx={filtroItemStyles}>
              <AppTextField
                appearance="dense"
                fullWidth
                label="Hasta"
                type="date"
                InputLabelProps={{ shrink: true }}
                value={opHasta ?? ""}
                onChange={(e) => setOpHasta(trimToNull(e.target.value))}
                variant="outlined"
              />
            </Box>
            <Box sx={filtroItemStyles}>
              <AppTextField
                appearance="dense"
                fullWidth
                label="Nº notificación"
                placeholder="Nº exacto (ej. 928 → 000928)"
                value={opNumNotif}
                onChange={(e) => setOpNumNotif(e.target.value)}
                variant="outlined"
              />
            </Box>
            <Box sx={filtroItemStyles}>
              <AppTextField
                appearance="dense"
                fullWidth
                label="Calle"
                placeholder="Ej. san martin"
                value={opCalleQ}
                onChange={(e) => setOpCalleQ(e.target.value)}
                variant="outlined"
              />
            </Box>
          </Box>
          <Box sx={filtroButtonsStyles}>
            <Button
              type="button"
              variant="contained"
              startIcon={<SearchIcon />}
              onClick={() => handleApplyOperativaFiltro()}
              sx={filtroButtonPrimaryStyles}
            >
              Buscar
            </Button>
            <Button
              type="button"
              variant="outlined"
              startIcon={<ClearIcon />}
              onClick={() => handleClearOperativaFiltro()}
              sx={filtroButtonSecondaryStyles}
            >
              Limpiar
            </Button>
          </Box>
        </Box>
      )}

      {mostrarTablaOperativa && (
        <>
          {operativaLoading ? (
            <BandejaTableSpinner />
          ) : (
            <NotificacionBandejaTable
              rows={filteredRowsOperativa}
              columns={esTabReinspeccionOperativa ? columnsReinspeccionOperativa : columnsOperativa}
              toolbar={renderOperativaToolbarRefresh}
              getRowId={
                esTabReinspeccionOperativa ? (row) => reinspeccionNotificacionBandejaRowKey(row) : undefined
              }
            />
          )}
        </>
      )}

      {mostrarHistorial && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Box sx={filtroContainerStyles}>
            <Typography sx={filtroTitleStyles}>Historial notificaciones</Typography>

            <Typography sx={filtroSectionTitleStyles}>Búsqueda específica</Typography>
            <Box sx={filtroGridStyles}>
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
                  label="Contribuyente"
                  value={histContribQ}
                  onChange={(e) => setHistContribQ(e.target.value)}
                  variant="outlined"
                />
              </Box>
              <Box sx={filtroItemStyles}>
                <AppSelect
                  appearance="dense"
                  fullWidth
                  label="Motivo / infracción"
                  value={histMotivoId === "" ? "" : String(histMotivoId)}
                  onChange={(e) =>
                    setHistMotivoId(e.target.value === "" ? "" : Number(e.target.value))
                  }
                  variant="outlined"
                  options={motivoSelectOptionsHistorial}
                />
              </Box>
            </Box>

            {historialNotificacionHasSpecificSearch({
              periodMode: histPeriodMode,
              mes: histMes,
              anio: histAnio,
              desde: histDesde,
              hasta: histHasta,
              distritoId: histDistritoId,
              numeroNotificacion: histNumNotif,
              calleQ: histCalleQ,
              contribuyenteQ: histContribQ,
              motivoId: histMotivoId,
              combinarConPeriodo: histCombinarConPeriodo,
            }) && (
              <FormControlLabel
                sx={{
                  mb: 1.5,
                  ml: 0,
                  "& .MuiFormControlLabel-label": {
                    color: "rgba(255,255,255,0.85)",
                    fontFamily: '"Tactic Sans", sans-serif',
                    fontSize: "0.85rem",
                  },
                }}
                control={
                  <Switch
                    size="small"
                    checked={histCombinarConPeriodo}
                    onChange={(e) => setHistCombinarConPeriodo(e.target.checked)}
                    color="primary"
                  />
                }
                label="Combinar también con período y filtros"
              />
            )}

            <Divider sx={{ borderColor: "rgba(255,255,255,0.12)", my: 2 }} />

            <Typography sx={filtroSectionTitleStyles}>Rango / período</Typography>
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
                      value={histMes === "" ? "" : String(histMes)}
                      onChange={(e) => setHistMes(e.target.value === "" ? "" : Number(e.target.value))}
                      variant="outlined"
                      options={MESES_OPTS_WITH_EMPTY}
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppSelect
                      appearance="dense"
                      fullWidth
                      label="Año"
                      value={histAnio === "" ? "" : String(histAnio)}
                      onChange={(e) => setHistAnio(e.target.value === "" ? "" : Number(e.target.value))}
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
            </Box>
            <Box sx={filtroButtonsStyles}>
              <AppButton
                dsVariant="ghost"
                dsSize="sm"
                onClick={() => {
                  setHistPeriodMode("month");
                  setHistMes("");
                  setHistAnio("");
                  setHistDesde(null);
                  setHistHasta(null);
                  setHistCombinarConPeriodo(false);
                  setHistDistritoId("");
                  setHistContribQ("");
                  setHistCalleQ("");
                  setHistNumNotif("");
                  setHistMotivoId("");
                  setHistorialFiltroAplicado(false);
                  setHistorialMeta(null);
                  setHistorialRows([]);
                  setHistorialError(null);
                  setHistorialApplied(null);
                  setHistorialPagination((prev) => resetClientPaginationPageIndex(prev));
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

          {historialLoading ? (
            <BandejaTableSpinner />
          ) : null}

          {!historialLoading && historialFiltroAplicado && (
            <>
              {historialMeta && (
                <BandejaTableSummary>
                  <BandejaTableSummaryItem label="Total" value={historialMeta.total} />
                  <BandejaTableSummaryItem
                    label="Mostrando"
                    value={`${historialPaginationSummary.visibleRows} de ${historialPaginationSummary.totalRows}`}
                  />
                  <BandejaTableSummaryItem
                    label="Página"
                    value={`${historialPaginationSummary.currentPage} de ${historialPaginationSummary.totalPages}`}
                  />
                  {historialApplied?.period.kind === "global" ? (
                    <BandejaTableSummaryItem
                      label="Período"
                      value="búsqueda global (sin rango)"
                    />
                  ) : (
                    historialMeta.desde &&
                    historialMeta.hasta && (
                      <BandejaTableSummaryItem
                        label="Rango"
                        value={`${historialMeta.desde} — ${historialMeta.hasta}`}
                      />
                    )
                  )}
                </BandejaTableSummary>
              )}
              <Box sx={{ width: "100%", minWidth: 0, maxWidth: "100%" }}>
                <NotificacionBandejaTable
                  rows={historialRows}
                  columns={columnsHistorial}
                  toolbar={renderHistorialToolbarRefresh}
                  documentalListViewport
                  getRowId={(row) => notificacionHistorialRowKey(row)}
                  pagination={historialPagination}
                  onPaginationChange={setHistorialPagination}
                  manualPagination
                  rowCount={historialMeta?.total ?? 0}
                />
              </Box>
            </>
          )}

          {!historialLoading && !historialFiltroAplicado && (
            <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, py: 1 }}>
              Usá búsqueda específica o elegí un período y tocá <strong>Filtrar</strong> para ver el listado.
            </Typography>
          )}
        </Box>
      )}

      <ExportDataDialog
        open={exportOpen}
        onClose={() => {
          if (exportLoading) return;
          setExportOpen(false);
        }}
        title="Exportar datos"
        subtitle="Notificaciones"
        loading={exportLoading}
        error={exportError}
        onClearError={() => setExportError(null)}
        showPeriod={
          !(plazoSlice === "total" && historialFiltroAplicado && historialApplied)
        }
        scopeHint={
          plazoSlice === "total" && historialFiltroAplicado && historialApplied
            ? "Se exportará el resultado filtrado actual."
            : undefined
        }
        onExport={handleExportNotificaciones}
      />

      <NotificacionDetalleDocumentalDialog
        open={modalOpen}
        onClose={closeModal}
        row={selected}
        variant={modalVariant}
        esReinspeccionNotificacion={modalEsReinspeccionNotificacion}
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
        saving={modalAltaExpedientePersisting}
        onGuardar={handleSave}
        onExpedienteMutacionExitosa={handleExpedienteMutacionExitosa}
      />
    </Box>
  );
};

export default GestionNotificacionPage;
