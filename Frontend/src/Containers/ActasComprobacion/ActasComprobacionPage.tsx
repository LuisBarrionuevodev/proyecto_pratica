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
  CircularProgress,
  Divider,
  FormControlLabel,
  IconButton,
  Paper,
  Switch,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  BandejaActaChipCell,
  BandejaDomicilioYRubroCell,
  BandejaEllipsisCell,
  BandejaFechaYChipOtCell,
  BandejaSegmentChipsCell,
  BANDEJA_MRT_BODY_CELL_PROPS,
  splitMiddleDot,
} from "../Actuaciones/Components/bandejaTableCells";
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";

import {
  createExpedienteDesdeActuacion,
  createOficioDesdeActuacion,
  fetchComprobacionDocumental,
  fetchOficiosByComprobacion,
  getActuacionesPendientesExpediente,
  getJuzgadosCatalogoCached,
  type IActuacionesPendientesItem,
  type IComprobacionDocumentalResponse,
  type ICreateExpedienteRequest,
  type IJuzgadoCatalogItem,
  type IPendientesOficioItem,
  type OficioComprobacionItem,
} from "../../api/actuacionesPendientesApi";
import {
  fetchComprobacionPendientesOficio,
  fetchComprobacionRecorridoDetalle,
  fetchPendientesReinspeccionOficio,
  type IComprobacionRecorridoDetalle,
  type IComprobacionRecorridoRow,
  type IReinspeccionOficioPendienteRow,
} from "../../api/actuacionesComprobacionActasApi";
import { containerStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { getCurrentMonthRange } from "../../utils/dateRange";
import { DARK_TABLE_CONFIG } from "../Actuaciones/styles/actuacionesTableStyles";
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
  metaInfoStyles,
  metaItemStyles,
  moduleContentColumnSx,
} from "../Actuaciones/styles/filtroStyles";
import { AppButton, AppSelect, AppTextField, ExportDataDialog } from "../../ui";
import { GLASS_COLORS, moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../styles/GlassStyles";
import { functionalPageShellSx } from "../../styles/functionalPageShell";
import { fetchDistritosCatalogo, type DistritoCatalogoItem } from "../../api/geolocalizacionApi";
import { useAppFeedback } from "../../components/feedback";
import { TableExportBoxStyles, TableExportButtonStyles } from "../../styles/TablasStyle";
import { applyFormErrorsFromApi, parseApiError } from "../../utils/parseApiError";
import {
  applyOficioAltaErrorsFromApi,
  validateOficioAltaPayloadClient,
} from "../../utils/oficioFormErrors";
import { contribuyenteBandejaLabel } from "../../utils/contribuyenteBandejaText";
import {
  formatActuacionListDomicilioLinea,
  type ActuacionListDomicilioLineaInput,
} from "../../utils/formatDomicilioLineaVisible";
import { ComprobacionExpedienteOperativoDialog } from "./components/ComprobacionExpedienteOperativoDialog";
import {
  ComprobacionOficioOperativoDialog,
  type ComprobacionOficioAltaPayload,
  type OficioOperativoRow,
} from "./components/ComprobacionOficioOperativoDialog";
import { ComprobacionReinspeccionDetalleDialog } from "./components/ComprobacionReinspeccionDetalleDialog";
import type { ReinspeccionOperativoDetalleRow } from "./components/comprobacionOperativoBlocks";
import { RecorridoDetalleDocumentalDialog } from "./components/RecorridoDetalleDocumentalDialog";
import { exportComprobacionesDataset } from "./utils/exportComprobacionesDataset";
import {
  buildRecorridoComprobacionFiltroPayload,
  fetchRecorridoComprobacionConPayload,
  recorridoComprobacionHasSpecificSearch,
  type RecorridoComprobacionFiltroPayload,
} from "./utils/buildRecorridoComprobacionFiltroPayload";
import {
  recCompOficioExpMotivoChips,
  recCompOficioExpMotivoSortKey,
  recorridoColumnChips,
  recorridoColumnSortKey,
} from "./utils/recorridoOficioExpLabels";
import {
  buildOperativaComprobacionFiltroPayload,
  type OperativaComprobacionFiltroPayload,
} from "./utils/buildOperativaComprobacionFiltroPayload";
import {
  notificacionEstadoOperativoChipColor,
  notificacionEstadoOperativoLabel,
} from "../GestionNotificacion/utils/notificacionEstadoOperativo";
import { humanizarEstadoIniciador, humanizarEstadoOperativoOficio } from "./utils/documentalLabelFormat";
import { perfLog, perfTimed } from "../../utils/perfLog";

type TabKey = "expediente" | "oficio" | "reinspeccion" | "recorrido";

const actasContentColumnSx = {
  ...moduleContentColumnSx,
  width: "100%",
  maxWidth: "100%",
  minWidth: 0,
};

type RecPeriodMode = "month" | "range";

function domicilioTextFromRow(r: ActuacionListDomicilioLineaInput): string {
  const t = formatActuacionListDomicilioLinea(r).trim();
  return t || "—";
}

function fechaOtLabel(fecha?: string | null, ot?: string | null): string {
  const f = (fecha ?? "").toString().trim() || "—";
  const o = (ot ?? "").toString().trim() || "—";
  return `${f} · ${o}`;
}

function contribBandejaFromRow(r: {
  contrib_apellido?: string | null;
  contrib_nombre?: string | null;
  razon_social?: string | null;
}): string {
  return contribuyenteBandejaLabel(r.contrib_apellido, r.contrib_nombre, r.razon_social);
}

function contribDocRecorrido(r: IComprobacionRecorridoRow): string {
  const c = contribBandejaFromRow(r);
  const d = (r.doc_nro ?? "").toString().trim();
  if (d) return `${c} · ${d}`;
  return c;
}

function contribDocRecorridoSegments(r: IComprobacionRecorridoRow): string[] {
  const full = contribDocRecorrido(r);
  const parts = splitMiddleDot(full);
  if (parts.length > 0) return parts;
  return full && full !== "—" ? [full] : [];
}

function reinOficioNumCompact(r: IReinspeccionOficioPendienteRow): string {
  const n = (r.oficio_numero ?? "").trim();
  const a = r.oficio_anio != null ? String(r.oficio_anio) : "";
  if (!n && !a) return "—";
  return [n, a].filter(Boolean).join("/");
}

function contribDocReinspeccion(r: IReinspeccionOficioPendienteRow): string {
  const c = contribBandejaFromRow(r);
  const d = (r.doc_nro ?? "").toString().trim();
  if (d) return `${c} · ${d}`;
  return c;
}

function contribDocReinspeccionSegments(r: IReinspeccionOficioPendienteRow): string[] {
  const full = contribDocReinspeccion(r);
  const parts = splitMiddleDot(full);
  if (parts.length > 0) return parts;
  return full && full !== "—" ? [full] : [];
}

/** Chips: acta de comprobación, oficio (n/año), motivo de infracción. */
function reinCompInfraccionChips(r: IReinspeccionOficioPendienteRow): string[] {
  const n = (r.acta_comprobacion_num ?? "").toString().trim();
  const comp = n ? `Comp. ${n}` : "Comp. —";
  const on = reinOficioNumCompact(r);
  const ofi = on !== "—" ? `Oficio ${on}` : "Oficio —";
  const inf = (r.comprobacion_motivo ?? "").toString().trim();
  return [comp, ofi, inf || "Sin infracción o motivo cargado"];
}

function reinCompInfraccionSortKey(r: IReinspeccionOficioPendienteRow): string {
  return reinCompInfraccionChips(r).join(" | ");
}

function reinBandejaRowKey(r: IReinspeccionOficioPendienteRow): string {
  return r.bandeja_row_key ?? `${r.id}-${r.oficio_id ?? 0}-${r.iniciador_id ?? 0}`;
}

function reinEstadoOficioChips(r: IReinspeccionOficioPendienteRow): string[] {
  const chips: string[] = [];
  if (r.estado_operativo) {
    chips.push(humanizarEstadoOperativoOficio(r.estado_operativo));
  } else if (r.en_ruta_borrador) {
    chips.push("Ruta borrador");
  } else if ((r.estado_iniciador ?? "").trim()) {
    chips.push(`Iniciador ${humanizarEstadoIniciador(r.estado_iniciador)}`);
  } else {
    chips.push("Sin iniciador");
  }
  if (r.editable === false && r.bloqueado_motivo) {
    chips.push("Bloqueado");
  }
  return chips;
}

/** Layout MRT compartido: menos altura de fila y ancho útil sin overflow horizontal del layout. */
const bandejaComprobacionMrtLayout = {
  density: "compact" as const,
  ...BANDEJA_MRT_BODY_CELL_PROPS,
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
};

const TIPO_FINAL_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "CUMPLE", label: "Cumple" },
  { value: "NO_CUMPLE", label: "No cumple" },
];

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

function trimToNull(s: string): string | null {
  const t = s.trim();
  return t || null;
}

function buildEstadoOperativoColumn<T extends { estado_operativo_pool?: string | null }>(): MRT_ColumnDef<T> {
  return {
    id: "estado_operativo",
    header: "Estado operativo",
    size: 132,
    accessorFn: (row) => notificacionEstadoOperativoLabel(row.estado_operativo_pool),
    Cell: ({ row }) => {
      const label = notificacionEstadoOperativoLabel(row.original.estado_operativo_pool);
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
  };
}

/**
 * Actas de comprobación: cuatro slices (expediente → oficio → reinspección → recorrido consultivo).
 */
const ActasComprobacionPage = () => {
  const feedback = useAppFeedback();
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const defaultMonthYear = useMemo(() => {
    const d = new Date(`${defaultRange.desde}T12:00:00`);
    return { mes: d.getMonth() + 1, anio: d.getFullYear() };
  }, [defaultRange.desde]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState<TabKey>("expediente");
  const deepLinkActuacionKeyDone = useRef<string | null>(null);
  const tabLoadedRef = useRef<Record<TabKey, boolean>>({
    expediente: false,
    oficio: false,
    reinspeccion: false,
    recorrido: false,
  });
  const [opDesde, setOpDesde] = useState<string | null>(null);
  const [opHasta, setOpHasta] = useState<string | null>(null);
  const [opNumComp, setOpNumComp] = useState("");
  const [opApplied, setOpApplied] = useState<OperativaComprobacionFiltroPayload | null>(null);
  const opAppliedRef = useRef<OperativaComprobacionFiltroPayload | null>(null);
  /** Solo para el slice Recorrido (selector de distrito). */
  const [distritosRecorrido, setDistritosRecorrido] = useState<DistritoCatalogoItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const r = await fetchDistritosCatalogo();
        if (!cancelled) setDistritosRecorrido(r.items ?? []);
      } catch {
        if (!cancelled) setDistritosRecorrido([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    opAppliedRef.current = opApplied;
  }, [opApplied]);

  const distritoSelectOptionsRecorrido = useMemo(
    () => [
      { value: "", label: "Todos los distritos" },
      ...distritosRecorrido.map((d) => ({ value: String(d.id), label: d.nombre })),
    ],
    [distritosRecorrido]
  );

  // —— Pendientes de expediente (comprobación sin expediente de envío)
  const [expItems, setExpItems] = useState<IActuacionesPendientesItem[]>([]);
  const [expTotalPendientes, setExpTotalPendientes] = useState(0);
  const [expLoading, setExpLoading] = useState(false);
  const [expError, setExpError] = useState<string | null>(null);
  const [selectedExp, setSelectedExp] = useState<IActuacionesPendientesItem | null>(null);
  const [modalExpOpen, setModalExpOpen] = useState(false);
  const [modalExpError, setModalExpError] = useState<string | null>(null);
  const [expNumeroForm, setExpNumeroForm] = useState("");
  const [expFechaForm, setExpFechaForm] = useState(defaultRange.hasta);
  const [savingExp, setSavingExp] = useState(false);
  const loadExpediente = useCallback(async (filters: OperativaComprobacionFiltroPayload | null = opAppliedRef.current) => {
    setExpLoading(true);
    setExpError(null);
    const hasDateRange = Boolean(filters?.desde || filters?.hasta);
    try {
      const resp = await perfTimed(
        "comprobacion.loadExpediente",
        () =>
          getActuacionesPendientesExpediente(filters?.desde ?? null, filters?.hasta ?? null, "comprobacion", null, {
            omitirRangoFecha: !hasDateRange,
            numeroComprobacion: filters?.numeroComprobacion ?? null,
          }),
        (r) => ({ rows: r.items.length, total: r.meta.total })
      );
      setExpItems(resp.items);
      setExpTotalPendientes(resp.meta.total);
      tabLoadedRef.current.expediente = true;
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setExpError(detail || "Error al cargar pendientes de expediente");
      setExpItems([]);
      setExpTotalPendientes(0);
    } finally {
      setExpLoading(false);
    }
  }, []);

  const openModalExp = useCallback(
    (row: IActuacionesPendientesItem) => {
      setSelectedExp(row);
      setExpNumeroForm("");
      setExpFechaForm(defaultRange.hasta);
      setModalExpError(null);
      setModalExpOpen(true);
    },
    [defaultRange.hasta]
  );

  const closeModalExp = () => {
    if (savingExp) return;
    setModalExpOpen(false);
    setSelectedExp(null);
  };

  const handleSaveExpediente = async () => {
    if (!selectedExp) return;
    if (!expNumeroForm.trim() || !expFechaForm) {
      setModalExpError("Completá número y fecha del expediente de comprobación");
      return;
    }
    setSavingExp(true);
    setModalExpError(null);
    try {
      const payload: ICreateExpedienteRequest = {
        expediente_numero: expNumeroForm.trim(),
        fecha_expediente: expFechaForm,
        source_type: "COMPROBACION",
      };
      await createExpedienteDesdeActuacion(selectedExp.id, payload);
      closeModalExp();
      await refreshActiveBandeja();
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setModalExpError(detail || "No se pudo añadir el expediente");
    } finally {
      setSavingExp(false);
    }
  };

  const columnsExpediente = useMemo<MRT_ColumnDef<IActuacionesPendientesItem>[]>(
    () => [
      {
        id: "fecha_ot",
        header: "Fecha · OT",
        size: 118,
        accessorFn: (r) => fechaOtLabel(r.fecha_actuacion, r.orden_trabajo_numero),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => (
          <BandejaFechaYChipOtCell
            fecha={(row.original.fecha_actuacion ?? "").toString().trim() || "—"}
            ot={(row.original.orden_trabajo_numero ?? "").toString().trim()}
          />
        ),
      },
      {
        id: "contrib",
        header: "Contribuyente",
        size: 152,
        accessorFn: (r) => contribBandejaFromRow(r),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => <BandejaEllipsisCell value={contribBandejaFromRow(row.original)} />,
      },
      {
        id: "domicilio_rubro",
        header: "Domicilio · rubro",
        size: 188,
        accessorFn: (r) => `${domicilioTextFromRow(r)} ${(r.rubro_nombre ?? "").trim()}`.trim(),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => (
          <BandejaDomicilioYRubroCell
            domicilioLinea={domicilioTextFromRow(row.original)}
            rubro={row.original.rubro_nombre}
          />
        ),
      },
      {
        accessorKey: "acta_comprobacion_num",
        header: "Nº comp.",
        size: 96,
        Cell: ({ row }) => {
          const n = (row.original.acta_comprobacion_num ?? "").trim();
          return <BandejaActaChipCell label={n ? `Comp. ${n}` : "—"} />;
        },
      },
      buildEstadoOperativoColumn<IActuacionesPendientesItem>(),
      {
        id: "acciones",
        header: "Acción",
        size: 152,
        grow: false,
        enableResizing: false,
        enableSorting: false,
        Cell: ({ row }) => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModalExp(row.original)}>
            Registrar expediente
          </AppButton>
        ),
      },
    ],
    [openModalExp]
  );

  const renderExpedienteToolbarRefresh = useCallback(
    () => (
      <Tooltip title="Actualizar listados">
        <span>
          <IconButton
            type="button"
            size="small"
            aria-label="Actualizar listados"
            disabled={expLoading}
            onClick={() => void loadExpediente()}
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
    [expLoading, loadExpediente]
  );

  const tableExpediente = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...bandejaComprobacionMrtLayout,
    columns: columnsExpediente,
    data: expItems,
    enableEditing: false,
    enableRowSelection: false,
    renderTopToolbarCustomActions: renderExpedienteToolbarRefresh,
  });

  // —— Pendientes de oficio (siempre mes corriente; sin filtro previo a la tabla)
  const [oficioApiTotal, setOficioApiTotal] = useState(0);
  const [oficioItems, setOficioItems] = useState<IPendientesOficioItem[]>([]);
  const [oficioLoading, setOficioLoading] = useState(false);
  const [oficioError, setOficioError] = useState<string | null>(null);
  const [juzgados, setJuzgados] = useState<IJuzgadoCatalogItem[]>([]);
  const [selectedOficio, setSelectedOficio] = useState<OficioOperativoRow | null>(null);
  const [modalOficioOpen, setModalOficioOpen] = useState(false);
  const [savingOficio, setSavingOficio] = useState(false);
  const [modalOficioError, setModalOficioError] = useState<string | null>(null);
  const [modalOficioFieldErrors, setModalOficioFieldErrors] = useState<Record<string, string>>({});
  const [modalDoc, setModalDoc] = useState<IComprobacionDocumentalResponse | null>(null);
  const [modalDocLoading, setModalDocLoading] = useState(false);
  const [modalDocError, setModalDocError] = useState<string | null>(null);
  const [modalOficios, setModalOficios] = useState<OficioComprobacionItem[]>([]);
  const [modalOficiosLoading, setModalOficiosLoading] = useState(false);
  const [modalOficiosError, setModalOficiosError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getJuzgadosCatalogoCached()
      .then((jz) => {
        if (!cancelled) setJuzgados(jz);
      })
      .catch(() => {
        if (!cancelled) setJuzgados([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadOficiosForComprobacion = useCallback(async (comprobacionId: number) => {
    setModalOficiosLoading(true);
    setModalOficiosError(null);
    try {
      const resp = await fetchOficiosByComprobacion(comprobacionId);
      setModalOficios(resp.oficios ?? []);
    } catch (err: unknown) {
      setModalOficios([]);
      const parsed = parseApiError(err, "No se pudo cargar el historial de oficios");
      setModalOficiosError(parsed.message);
    } finally {
      setModalOficiosLoading(false);
    }
  }, []);

  const loadOficio = useCallback(async (filters: OperativaComprobacionFiltroPayload | null = opAppliedRef.current) => {
    setOficioLoading(true);
    setOficioError(null);
    const hasDateRange = Boolean(filters?.desde || filters?.hasta);
    try {
      const resp = await perfTimed(
        "comprobacion.loadOficio",
        () =>
          fetchComprobacionPendientesOficio(filters?.desde ?? null, filters?.hasta ?? null, null, {
            omitirRangoFecha: !hasDateRange,
            numeroComprobacion: filters?.numeroComprobacion ?? null,
          }),
        (r) => ({ rows: r.items.length, total: r.meta.total })
      );
      setOficioApiTotal(resp.meta.total);
      setOficioItems(resp.items);
      tabLoadedRef.current.oficio = true;
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setOficioError(detail || "Error al cargar pendientes de oficio");
      setOficioItems([]);
      setOficioApiTotal(0);
    } finally {
      setOficioLoading(false);
    }
  }, []);

  const openModalOficio = useCallback(
    async (row: OficioOperativoRow) => {
      setSelectedOficio(row);
      setModalOficioError(null);
      setModalDoc(null);
      setModalDocError(null);
      setModalOficios([]);
      setModalOficiosError(null);
      setModalOficioOpen(true);
      setModalDocLoading(true);
      setModalOficiosLoading(false);
      perfLog("comprobacion.modal.oficio.open", { actuacionId: row.id });
      try {
        const doc = await perfTimed(
          "comprobacion.modal.oficio.documental",
          () => fetchComprobacionDocumental(row.id),
          () => ({ actuacionId: row.id })
        );
        setModalDoc(doc);
        setModalDocError(null);
        void loadOficiosForComprobacion(doc.comprobacion_id);
      } catch (err: unknown) {
        setModalDoc(null);
        const parsed = parseApiError(
          err,
          "No se pudo cargar la ficha documental (no se mostrará edición ni el bloqueo por trámite en ruta hasta reintentar)."
        );
        setModalDocError(parsed.message);
      } finally {
        setModalDocLoading(false);
      }
    },
    [loadOficiosForComprobacion]
  );

  useEffect(() => {
    const t = searchParams.get("tab");
    if (t === "expediente" || t === "oficio" || t === "reinspeccion" || t === "recorrido") {
      setTab(t);
    }
  }, [searchParams]);

  useEffect(() => {
    const raw = searchParams.get("actuacionId");
    if (!raw) {
      deepLinkActuacionKeyDone.current = null;
      return;
    }
    const urlTab = searchParams.get("tab");
    const effectiveTab: TabKey =
      urlTab === "expediente" || urlTab === "oficio" || urlTab === "reinspeccion" || urlTab === "recorrido"
        ? urlTab
        : tab;
    const key = `${effectiveTab}:${raw}`;
    if (deepLinkActuacionKeyDone.current === key) return;

    const aid = Number.parseInt(raw, 10);
    if (!Number.isFinite(aid)) return;

    const markDoneAndClear = () => {
      deepLinkActuacionKeyDone.current = key;
      const next = new URLSearchParams(searchParams);
      next.delete("actuacionId");
      setSearchParams(next, { replace: true });
    };

    if (effectiveTab === "expediente" && !expLoading) {
      const row = expItems.find((r) => r.id === aid);
      if (row) openModalExp(row);
      markDoneAndClear();
      return;
    }
    if (effectiveTab === "oficio" && !oficioLoading) {
      const row = oficioItems.find((r) => r.id === aid);
      if (row) void openModalOficio(row);
      markDoneAndClear();
      return;
    }
    if (effectiveTab === "recorrido") {
      markDoneAndClear();
      return;
    }
    if (effectiveTab === "reinspeccion") {
      markDoneAndClear();
    }
  }, [
    tab,
    searchParams,
    setSearchParams,
    expLoading,
    oficioLoading,
    expItems,
    oficioItems,
    openModalExp,
    openModalOficio,
  ]);

  const closeModalOficio = () => {
    if (savingOficio) return;
    setModalOficioOpen(false);
    setSelectedOficio(null);
    setModalDoc(null);
    setModalDocError(null);
    setModalDocLoading(false);
    setModalOficios([]);
    setModalOficiosError(null);
    setModalOficiosLoading(false);
    setModalOficioError(null);
    setModalOficioFieldErrors({});
  };

  const columnsOficio = useMemo<MRT_ColumnDef<IPendientesOficioItem>[]>(
    () => [
      {
        id: "fecha_ot",
        header: "Fecha · OT",
        size: 118,
        accessorFn: (r) => fechaOtLabel(r.fecha_actuacion, r.orden_trabajo_numero),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => (
          <BandejaFechaYChipOtCell
            fecha={(row.original.fecha_actuacion ?? "").toString().trim() || "—"}
            ot={(row.original.orden_trabajo_numero ?? "").toString().trim()}
          />
        ),
      },
      {
        id: "contrib",
        header: "Contribuyente",
        size: 152,
        accessorFn: (r) => contribBandejaFromRow(r),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => <BandejaEllipsisCell value={contribBandejaFromRow(row.original)} />,
      },
      {
        id: "domicilio_rubro",
        header: "Domicilio · rubro",
        size: 188,
        accessorFn: (r) => `${domicilioTextFromRow(r)} ${(r.rubro_nombre ?? "").trim()}`.trim(),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => (
          <BandejaDomicilioYRubroCell
            domicilioLinea={domicilioTextFromRow(row.original)}
            rubro={row.original.rubro_nombre}
          />
        ),
      },
      {
        accessorKey: "acta_comprobacion_num",
        header: "Nº comp.",
        size: 96,
        Cell: ({ row }) => {
          const n = (row.original.acta_comprobacion_num ?? "").trim();
          return <BandejaActaChipCell label={n ? `Comp. ${n}` : "—"} />;
        },
      },
      {
        id: "estado_doc",
        header: "Estado",
        size: 132,
        accessorFn: () => "Pendiente oficio (manual)",
        Cell: () => <BandejaEllipsisCell value="Pendiente oficio (manual)" />,
      },
      buildEstadoOperativoColumn<IPendientesOficioItem>(),
      {
        id: "acciones",
        header: "Acción",
        size: 128,
        grow: false,
        enableResizing: false,
        enableSorting: false,
        Cell: ({ row }) => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => void openModalOficio(row.original)}>
            Registrar oficio
          </AppButton>
        ),
      },
    ],
    [openModalOficio]
  );

  const renderOficioToolbarRefresh = useCallback(
    () => (
      <Tooltip title="Actualizar listados">
        <span>
          <IconButton
            type="button"
            size="small"
            aria-label="Actualizar listados"
            disabled={oficioLoading}
            onClick={() => void loadOficio()}
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
    [oficioLoading, loadOficio]
  );

  const tableOficio = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...bandejaComprobacionMrtLayout,
    columns: columnsOficio,
    data: oficioItems,
    enableEditing: false,
    enableRowSelection: false,
    renderTopToolbarCustomActions: renderOficioToolbarRefresh,
  });

  // —— Reinspección (sin filtro por mes: `omitir_rango_fecha` en API; refresco en toolbar)
  const [reinApiTotal, setReinApiTotal] = useState(0);
  const [reinItems, setReinItems] = useState<IReinspeccionOficioPendienteRow[]>([]);
  const [reinLoading, setReinLoading] = useState(false);
  const [reinError, setReinError] = useState<string | null>(null);
  const [modalReinOpen, setModalReinOpen] = useState(false);
  const [selectedRein, setSelectedRein] = useState<ReinspeccionOperativoDetalleRow | null>(null);

  const openModalRein = useCallback((r: IReinspeccionOficioPendienteRow) => {
    setSelectedRein(r as ReinspeccionOperativoDetalleRow);
    setModalReinOpen(true);
  }, []);

  const closeModalRein = useCallback(() => {
    setModalReinOpen(false);
    setSelectedRein(null);
  }, []);

  const loadRein = useCallback(async (filters: OperativaComprobacionFiltroPayload | null = opAppliedRef.current) => {
    setReinLoading(true);
    setReinError(null);
    const hasDateRange = Boolean(filters?.desde || filters?.hasta);
    try {
      const resp = await perfTimed(
        "comprobacion.loadReinspeccion",
        () =>
          fetchPendientesReinspeccionOficio(filters?.desde ?? null, filters?.hasta ?? null, null, {
            omitirRangoFecha: !hasDateRange,
            numeroComprobacion: filters?.numeroComprobacion ?? null,
          }),
        (r) => ({ rows: r.items.length, total: r.meta.total })
      );
      setReinApiTotal(resp.meta.total);
      setReinItems(resp.items);
      tabLoadedRef.current.reinspeccion = true;
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setReinError(detail || "Error al cargar pendientes de reinspección");
      setReinItems([]);
      setReinApiTotal(0);
    } finally {
      setReinLoading(false);
    }
  }, []);

  const invalidatePendientesTabs = useCallback(() => {
    tabLoadedRef.current.expediente = false;
    tabLoadedRef.current.oficio = false;
    tabLoadedRef.current.reinspeccion = false;
  }, []);

  const handleApplyOperativaFiltro = useCallback(() => {
    const payload = buildOperativaComprobacionFiltroPayload({
      desde: opDesde,
      hasta: opHasta,
      numeroComprobacion: opNumComp,
    });
    setOpApplied(payload);
    opAppliedRef.current = payload;
    invalidatePendientesTabs();
    if (tab === "expediente") void loadExpediente(payload);
    else if (tab === "oficio") void loadOficio(payload);
    else if (tab === "reinspeccion") void loadRein(payload);
  }, [opDesde, opHasta, opNumComp, tab, invalidatePendientesTabs, loadExpediente, loadOficio, loadRein]);

  const handleClearOperativaFiltro = useCallback(() => {
    setOpDesde(null);
    setOpHasta(null);
    setOpNumComp("");
    setOpApplied(null);
    opAppliedRef.current = null;
    invalidatePendientesTabs();
    if (tab === "expediente") void loadExpediente(null);
    else if (tab === "oficio") void loadOficio(null);
    else if (tab === "reinspeccion") void loadRein(null);
  }, [tab, invalidatePendientesTabs, loadExpediente, loadOficio, loadRein]);

  /** Lazy-load por tab con cache; Recorrido sigue cargando solo con Filtrar. */
  const ensureTabLoaded = useCallback(
    async (key: TabKey, options?: { force?: boolean }) => {
      const force = options?.force ?? false;
      if (key === "recorrido") return;
      if (!force && tabLoadedRef.current[key]) {
        perfLog("comprobacion.tab.cacheHit", { tab: key });
        return;
      }
      perfLog("comprobacion.tab.fetch", { tab: key, force });
      if (key === "expediente") await loadExpediente();
      else if (key === "oficio") await loadOficio();
      else if (key === "reinspeccion") await loadRein();
      tabLoadedRef.current[key] = true;
    },
    [loadExpediente, loadOficio, loadRein]
  );

  const onReinBandejasActualizadas = useCallback(async () => {
    tabLoadedRef.current.reinspeccion = false;
    await ensureTabLoaded("reinspeccion", { force: true });
  }, [ensureTabLoaded]);

  const selectedReinKey = selectedRein != null ? reinBandejaRowKey(selectedRein) : null;
  useEffect(() => {
    if (!modalReinOpen || selectedReinKey == null) return;
    const found = reinItems.find((r) => reinBandejaRowKey(r) === selectedReinKey);
    if (found) setSelectedRein(found as ReinspeccionOperativoDetalleRow);
  }, [reinItems, modalReinOpen, selectedReinKey]);

  /** Refetch puntual del modal de oficio (documental + lista de oficios de la comprobación). */
  const refreshModalOficioData = useCallback(async () => {
    if (!selectedOficio) return;
    try {
      const doc = await fetchComprobacionDocumental(selectedOficio.id);
      setModalDoc(doc);
      setModalDocError(null);
      await loadOficiosForComprobacion(doc.comprobacion_id);
    } catch (err: unknown) {
      setModalDoc(null);
      const parsed = parseApiError(err, "No se pudo recargar la ficha documental (edición no disponible hasta reintentar).");
      setModalDocError(parsed.message);
    }
  }, [selectedOficio, loadOficiosForComprobacion]);

  /** Refresca solo la bandeja del slice activo (sin catálogos ni otras pestañas). */
  const refreshActiveBandeja = useCallback(async () => {
    if (tab === "recorrido") return;
    await ensureTabLoaded(tab, { force: true });
  }, [tab, ensureTabLoaded]);

  const reloadOficioModalDocumental = useCallback(async () => {
    await refreshModalOficioData();
    await refreshActiveBandeja();
  }, [refreshModalOficioData, refreshActiveBandeja]);

  const handleSaveOficio = useCallback(
    async (payload: ComprobacionOficioAltaPayload) => {
      if (!selectedOficio) return;
      const clientFe = validateOficioAltaPayloadClient(payload);
      setModalOficioFieldErrors(clientFe);
      if (Object.keys(clientFe).length > 0) {
        setModalOficioError(null);
        return;
      }
      setSavingOficio(true);
      setModalOficioError(null);
      setModalOficioFieldErrors({});
      try {
        await createOficioDesdeActuacion(selectedOficio.id, {
          numero_oficio: payload.numero_oficio.trim(),
          fecha_oficio: payload.fecha_oficio,
          juzgado_id: Number(payload.juzgado_id),
          causa: payload.causa,
          numero_expediente_oficio: payload.numero_expediente_oficio.trim(),
          fecha_expediente_oficio: payload.fecha_expediente_oficio,
        });
        feedback.success("Oficio registrado correctamente.");
        setModalOficioError(null);
        setModalOficioFieldErrors({});
        await refreshModalOficioData();
        await refreshActiveBandeja();
      } catch (err: unknown) {
        const parsed = applyOficioAltaErrorsFromApi(err);
        setModalOficioFieldErrors(parsed.fieldErrors);
        setModalOficioError(parsed.globalMessage);
      } finally {
        setSavingOficio(false);
      }
    },
    [selectedOficio, refreshModalOficioData, refreshActiveBandeja, feedback]
  );

  const columnsRein = useMemo<MRT_ColumnDef<IReinspeccionOficioPendienteRow>[]>(
    () => [
      {
        id: "fecha_ot",
        header: "Fecha · OT",
        size: 118,
        accessorFn: (r) => fechaOtLabel(r.fecha_actuacion, r.orden_trabajo_numero),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => (
          <BandejaFechaYChipOtCell
            fecha={(row.original.fecha_actuacion ?? "").toString().trim() || "—"}
            ot={(row.original.orden_trabajo_numero ?? "").toString().trim()}
          />
        ),
      },
      {
        id: "contrib_doc",
        header: "Titular · doc.",
        size: 168,
        accessorFn: (r) => contribDocReinspeccion(r),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => {
          const segs = contribDocReinspeccionSegments(row.original);
          return segs.length > 1 ? (
            <BandejaSegmentChipsCell segments={segs} />
          ) : (
            <BandejaEllipsisCell value={contribDocReinspeccion(row.original)} />
          );
        },
      },
      {
        id: "domicilio_rubro",
        header: "Domicilio · rubro",
        size: 176,
        accessorFn: (r) => `${domicilioTextFromRow(r)} ${(r.rubro_nombre ?? "").trim()}`.trim(),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => (
          <BandejaDomicilioYRubroCell
            domicilioLinea={domicilioTextFromRow(row.original)}
            rubro={row.original.rubro_nombre}
          />
        ),
      },
      {
        id: "comp_infraccion",
        header: "Comprobación",
        size: 280,
        accessorFn: (r) => reinCompInfraccionSortKey(r),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => <BandejaSegmentChipsCell segments={reinCompInfraccionChips(row.original)} />,
      },
      {
        id: "estado_oficio",
        header: "Estado oficio",
        size: 150,
        accessorFn: (r) => reinEstadoOficioChips(r).join(" · "),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => <BandejaSegmentChipsCell segments={reinEstadoOficioChips(row.original)} />,
      },
      buildEstadoOperativoColumn<IReinspeccionOficioPendienteRow>(),
      {
        id: "accion_rein",
        header: "Acción",
        size: 148,
        grow: false,
        enableResizing: false,
        enableSorting: false,
        Cell: ({ row }) => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModalRein(row.original)}>
            Gestionar oficio
          </AppButton>
        ),
      },
    ],
    [openModalRein]
  );

  const renderReinToolbarRefresh = useCallback(
    () => (
      <Tooltip title="Actualizar listados">
        <span>
          <IconButton
            type="button"
            size="small"
            aria-label="Actualizar listados"
            disabled={reinLoading}
            onClick={() => void loadRein()}
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
    [reinLoading, loadRein]
  );

  const tableRein = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...bandejaComprobacionMrtLayout,
    columns: columnsRein,
    data: reinItems,
    getRowId: (row) => reinBandejaRowKey(row),
    enableEditing: false,
    enableRowSelection: false,
    renderTopToolbarCustomActions: renderReinToolbarRefresh,
  });

  // —— Recorrido (período acotado vs buscador de texto)
  const [recPeriodMode, setRecPeriodMode] = useState<RecPeriodMode>("month");
  const [recMes, setRecMes] = useState<number | "">("");
  const [recAnio, setRecAnio] = useState<number | "">("");
  const [recDesde, setRecDesde] = useState<string | null>(null);
  const [recHasta, setRecHasta] = useState<string | null>(null);
  const [recCombinarConPeriodo, setRecCombinarConPeriodo] = useState(false);
  const [recDistritoId, setRecDistritoId] = useState<number | "">("");
  const [recContrib, setRecContrib] = useState("");
  const [recCalle, setRecCalle] = useState("");
  const [recActa, setRecActa] = useState("");
  const [recOfi, setRecOfi] = useState("");
  const [recExpediente, setRecExpediente] = useState("");
  const [recTipoFinal, setRecTipoFinal] = useState("");
  const [recItems, setRecItems] = useState<IComprobacionRecorridoRow[]>([]);
  const [recFilterApplied, setRecFilterApplied] = useState(false);
  const [recAppliedPayload, setRecAppliedPayload] = useState<RecorridoComprobacionFiltroPayload | null>(null);
  const [recMeta, setRecMeta] = useState<{ total: number; desde: string | null; hasta: string | null } | null>(null);
  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState<string | null>(null);
  const [detalleOpen, setDetalleOpen] = useState(false);
  const [detalleLoading, setDetalleLoading] = useState(false);
  const [detalle, setDetalle] = useState<IComprobacionRecorridoDetalle | null>(null);
  const [detalleActuacionId, setDetalleActuacionId] = useState<number | null>(null);
  /** Fila del listado Recorrido al abrir detalle (enriquece domicilio / inspectores sin otro endpoint). */
  const [detalleListRow, setDetalleListRow] = useState<IComprobacionRecorridoRow | null>(null);

  const [exportOpen, setExportOpen] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const reloadRecorridoDetalle = useCallback(async (actuacionId: number) => {
    const d = await fetchComprobacionRecorridoDetalle(actuacionId);
    setDetalle(d);
  }, []);

  const loadRecorridoSearch = useCallback(async (payload: RecorridoComprobacionFiltroPayload) => {
    setRecLoading(true);
    setRecError(null);
    try {
      const resp = await perfTimed(
        "comprobacion.loadRecorrido",
        () => fetchRecorridoComprobacionConPayload(payload),
        (r) => ({ rows: r.items.length, total: r.meta.total })
      );
      setRecItems(resp.items as IComprobacionRecorridoRow[]);
      setRecMeta({
        total: resp.meta.total,
        desde: resp.meta.desde,
        hasta: resp.meta.hasta,
      });
      setRecAppliedPayload(payload);
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setRecError(detail || "Error al cargar recorrido");
      setRecItems([]);
      setRecMeta(null);
    } finally {
      setRecLoading(false);
    }
  }, []);

  const aplicarFiltroRecorrido = useCallback(() => {
    const built = buildRecorridoComprobacionFiltroPayload({
      periodMode: recPeriodMode,
      mes: recMes,
      anio: recAnio,
      desde: recDesde,
      hasta: recHasta,
      distritoId: recDistritoId,
      actaComprobacion: recActa,
      calleQ: recCalle,
      contribuyenteQ: recContrib,
      oficioNumero: recOfi,
      expedienteNumero: recExpediente,
      tipoFinal: recTipoFinal,
      combinarConPeriodo: recCombinarConPeriodo,
    });
    if (!built.ok) {
      setRecError(built.error);
      return;
    }
    setRecFilterApplied(true);
    void loadRecorridoSearch(built.payload);
  }, [
    loadRecorridoSearch,
    recPeriodMode,
    recMes,
    recAnio,
    recDesde,
    recHasta,
    recDistritoId,
    recContrib,
    recCalle,
    recActa,
    recOfi,
    recExpediente,
    recTipoFinal,
    recCombinarConPeriodo,
  ]);

  useEffect(() => {
    void ensureTabLoaded(tab);
  }, [tab, ensureTabLoaded]);

  const openDetalle = useCallback(
    async (row: IComprobacionRecorridoRow) => {
      const actuacionId = row.id;
      setDetalleListRow(row);
      setDetalleActuacionId(actuacionId);
      setDetalleOpen(true);
      setDetalleLoading(true);
      setDetalle(null);
      try {
        await reloadRecorridoDetalle(actuacionId);
      } catch (err: unknown) {
        const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
        setRecError(detail || "No se pudo cargar el detalle");
        setDetalleOpen(false);
        setDetalleListRow(null);
      } finally {
        setDetalleLoading(false);
      }
    },
    [reloadRecorridoDetalle]
  );

  const columnsRec = useMemo<MRT_ColumnDef<IComprobacionRecorridoRow>[]>(
    () => [
      {
        id: "fecha_ot",
        header: "Fecha · OT",
        size: 118,
        accessorFn: (r) => fechaOtLabel(r.fecha_actuacion, r.orden_trabajo_numero),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => (
          <BandejaFechaYChipOtCell
            fecha={(row.original.fecha_actuacion ?? "").toString().trim() || "—"}
            ot={(row.original.orden_trabajo_numero ?? "").toString().trim()}
          />
        ),
      },
      {
        id: "contrib_doc",
        header: "Titular · doc.",
        size: 168,
        accessorFn: (r) => contribDocRecorrido(r),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => {
          const segs = contribDocRecorridoSegments(row.original);
          return segs.length > 1 ? (
            <BandejaSegmentChipsCell segments={segs} />
          ) : (
            <BandejaEllipsisCell value={contribDocRecorrido(row.original)} />
          );
        },
      },
      {
        id: "domicilio_rubro",
        header: "Domicilio · rubro",
        size: 176,
        accessorFn: (r) => `${domicilioTextFromRow(r)} ${(r.rubro_nombre ?? "").trim()}`.trim(),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => (
          <BandejaDomicilioYRubroCell
            domicilioLinea={domicilioTextFromRow(row.original)}
            rubro={row.original.rubro_nombre}
          />
        ),
      },
      {
        id: "comp_oficio_exp",
        header: "Nº comp. · oficio · exp. · motivo",
        size: 320,
        accessorFn: (r) => recCompOficioExpMotivoSortKey(r),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => <BandejaSegmentChipsCell segments={recCompOficioExpMotivoChips(row.original)} />,
      },
      {
        id: "recorrido_visitas",
        header: "Recorrido",
        size: 280,
        accessorFn: (r) => recorridoColumnSortKey(r),
        sortingFn: "alphanumeric",
        Cell: ({ row }) => <BandejaSegmentChipsCell segments={recorridoColumnChips(row.original)} />,
      },
      {
        id: "ver",
        header: "Acción",
        size: 108,
        grow: false,
        enableResizing: false,
        enableSorting: false,
        Cell: ({ row }) => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => void openDetalle(row.original)}>
            Ver detalle
          </AppButton>
        ),
      },
    ],
    [openDetalle]
  );

  const tableRec = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...bandejaComprobacionMrtLayout,
    columns: columnsRec,
    data: recItems,
    enableEditing: false,
    enableRowSelection: false,
  });

  const tabIndex =
    tab === "expediente" ? 0 : tab === "oficio" ? 1 : tab === "reinspeccion" ? 2 : 3;

  const handleExportComprobaciones = useCallback(
    async (options: {
      format: "excel" | "pdf";
      periodMode: "workweek" | "month" | "custom";
      desde: string;
      hasta: string;
    }) => {
      setExportLoading(true);
      setExportError(null);
      try {
        const recorridoCtx =
          tab === "recorrido" && recAppliedPayload
            ? {
                distritoId: recAppliedPayload.distritoId,
                contribuyenteQ: recAppliedPayload.contrib_q ?? null,
                calleQ: recAppliedPayload.calle_q ?? null,
                actaComprobacion: recAppliedPayload.acta_comprobacion ?? null,
                oficioNumero: recAppliedPayload.oficio_numero ?? null,
                expedienteNumero: recAppliedPayload.expediente_numero ?? null,
                tipoFinal: recAppliedPayload.tipo_final ?? null,
              }
            : {};

        await exportComprobacionesDataset({
          format: options.format,
          desde: options.desde,
          hasta: options.hasta,
          slice: tab,
          ...recorridoCtx,
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
    [feedback, tab, recAppliedPayload]
  );

  return (
    <Box sx={containerStyles}>
      <Box sx={{ ...functionalPageShellSx, ...actasContentColumnSx }}>
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
              value={tabIndex}
              onChange={(_, v) => {
                setTab(
                  v === 0 ? "expediente" : v === 1 ? "oficio" : v === 2 ? "reinspeccion" : "recorrido"
                );
              }}
              variant="scrollable"
              allowScrollButtonsMobile
              sx={{ ...moduleSlicesTabsSx, flex: 1, minWidth: 0 }}
            >
              <Tab
                label={`Pendientes de expediente · ${
                  tab === "expediente" && expLoading ? "…" : expTotalPendientes
                }`}
              />
              <Tab
                label={`Pendientes de oficio · ${
                  tab === "oficio" && oficioLoading ? "…" : oficioApiTotal
                }`}
              />
              <Tab
                label={`Pendientes de reinspección · ${
                  tab === "reinspeccion" && reinLoading ? "…" : reinApiTotal
                }`}
              />
              <Tab label="Recorrido" />
            </Tabs>
            {tab === "recorrido" && (
              <Box sx={{ ...TableExportBoxStyles, p: 0, flexDirection: "row", flexShrink: 0 }}>
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
          </Paper>

          {(tab === "expediente" || tab === "oficio" || tab === "reinspeccion") && (
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
                    label="Nº comprobación"
                    placeholder="Fragmento del acta"
                    value={opNumComp}
                    onChange={(e) => setOpNumComp(e.target.value)}
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

          {tab === "expediente" && (
            <>
              {expError && (
                <Alert severity="error" sx={alertBaseStyles}>
                  {expError}
                </Alert>
              )}
              {expLoading && expItems.length === 0 && !expError ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
                  <CircularProgress size={28} sx={{ color: COLORS.primary }} />
                </Box>
              ) : (
                <Box sx={{ position: "relative", opacity: expLoading ? 0.65 : 1, transition: "opacity 0.2s" }}>
                  {expLoading && expItems.length > 0 && (
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
                  <MaterialReactTable table={tableExpediente} />
                </Box>
              )}
            </>
          )}

          {tab === "oficio" && (
            <>
              <Alert severity="info" sx={{ ...alertBaseStyles, mb: 1.5 }}>
                Esta bandeja lista actas <strong>sin ningún oficio</strong>. Si ya cargaste un oficio y necesitás
                agregar otro, usá <strong>Pendiente de reinspección</strong> → «Gestionar oficio» → «Agregar otro
                oficio».
              </Alert>
              {oficioError && (
                <Alert severity="error" sx={alertBaseStyles}>
                  {oficioError}
                </Alert>
              )}
              {oficioLoading && oficioItems.length === 0 && !oficioError ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
                  <CircularProgress size={28} sx={{ color: COLORS.primary }} />
                </Box>
              ) : (
                <Box sx={{ position: "relative", opacity: oficioLoading ? 0.65 : 1, transition: "opacity 0.2s" }}>
                  {oficioLoading && oficioItems.length > 0 && (
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
                  <MaterialReactTable table={tableOficio} />
                </Box>
              )}
            </>
          )}

          {tab === "reinspeccion" && (
            <>
              {reinError && (
                <Alert severity="error" sx={alertBaseStyles}>
                  {reinError}
                </Alert>
              )}
              {reinLoading && reinItems.length === 0 && !reinError ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
                  <CircularProgress size={28} sx={{ color: COLORS.primary }} />
                </Box>
              ) : !reinLoading && !reinError && reinItems.length === 0 ? (
                <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, py: 2 }}>
                  No hay comprobaciones pendientes de reinspección.
                </Typography>
              ) : (
                <Box sx={{ position: "relative", opacity: reinLoading ? 0.65 : 1, transition: "opacity 0.2s" }}>
                  {reinLoading && reinItems.length > 0 && (
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
                  <MaterialReactTable table={tableRein} />
                </Box>
              )}
            </>
          )}

          {tab === "recorrido" && (
            <>
              <Box sx={filtroContainerStyles}>
                <Typography sx={filtroTitleStyles}>Recorrido del acta de comprobación</Typography>

                <Typography sx={filtroSectionTitleStyles}>Búsqueda específica</Typography>
                <Box sx={filtroGridStyles}>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      label="Nº acta comprobación"
                      value={recActa}
                      onChange={(e) => setRecActa(e.target.value)}
                      variant="outlined"
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      label="Calle"
                      value={recCalle}
                      onChange={(e) => setRecCalle(e.target.value)}
                      variant="outlined"
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      label="Contribuyente"
                      value={recContrib}
                      onChange={(e) => setRecContrib(e.target.value)}
                      variant="outlined"
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      label="Nº oficio (texto)"
                      value={recOfi}
                      onChange={(e) => setRecOfi(e.target.value)}
                      variant="outlined"
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      label="Nº expediente"
                      value={recExpediente}
                      onChange={(e) => setRecExpediente(e.target.value)}
                      variant="outlined"
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppSelect
                      appearance="dense"
                      fullWidth
                      label="Tipo final"
                      value={recTipoFinal}
                      onChange={(e) => setRecTipoFinal(String(e.target.value))}
                      variant="outlined"
                      options={TIPO_FINAL_OPTIONS}
                    />
                  </Box>
                </Box>

                {recorridoComprobacionHasSpecificSearch({
                  periodMode: recPeriodMode,
                  mes: recMes,
                  anio: recAnio,
                  desde: recDesde,
                  hasta: recHasta,
                  distritoId: recDistritoId,
                  actaComprobacion: recActa,
                  calleQ: recCalle,
                  contribuyenteQ: recContrib,
                  oficioNumero: recOfi,
                  expedienteNumero: recExpediente,
                  tipoFinal: recTipoFinal,
                  combinarConPeriodo: recCombinarConPeriodo,
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
                        checked={recCombinarConPeriodo}
                        onChange={(e) => setRecCombinarConPeriodo(e.target.checked)}
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
                      value={recPeriodMode}
                      onChange={(e) => setRecPeriodMode(e.target.value as RecPeriodMode)}
                      variant="outlined"
                      options={[
                        { value: "month", label: "Mes y año" },
                        { value: "range", label: "Fecha desde / hasta" },
                      ]}
                    />
                  </Box>
                  {recPeriodMode === "month" ? (
                    <>
                      <Box sx={filtroItemStyles}>
                        <AppSelect
                          appearance="dense"
                          fullWidth
                          label="Mes"
                          value={recMes === "" ? "" : String(recMes)}
                          onChange={(e) => setRecMes(e.target.value === "" ? "" : Number(e.target.value))}
                          variant="outlined"
                          options={MESES_OPTS_WITH_EMPTY}
                        />
                      </Box>
                      <Box sx={filtroItemStyles}>
                        <AppSelect
                          appearance="dense"
                          fullWidth
                          label="Año"
                          value={recAnio === "" ? "" : String(recAnio)}
                          onChange={(e) => setRecAnio(e.target.value === "" ? "" : Number(e.target.value))}
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
                          value={recDesde ?? ""}
                          onChange={(e) => setRecDesde(e.target.value || null)}
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
                          value={recHasta ?? ""}
                          onChange={(e) => setRecHasta(e.target.value || null)}
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
                      value={recDistritoId === "" ? "" : String(recDistritoId)}
                      onChange={(e) => {
                        const v = e.target.value;
                        setRecDistritoId(v === "" ? "" : Number(v));
                      }}
                      variant="outlined"
                      options={distritoSelectOptionsRecorrido}
                    />
                  </Box>
                </Box>
                <Box sx={filtroButtonsStyles}>
                  <AppButton
                    dsVariant="ghost"
                    dsSize="sm"
                    onClick={() => {
                      setRecPeriodMode("month");
                      setRecMes("");
                      setRecAnio("");
                      setRecDesde(null);
                      setRecHasta(null);
                      setRecCombinarConPeriodo(false);
                      setRecDistritoId("");
                      setRecContrib("");
                      setRecCalle("");
                      setRecActa("");
                      setRecOfi("");
                      setRecExpediente("");
                      setRecTipoFinal("");
                      setRecFilterApplied(false);
                      setRecAppliedPayload(null);
                      setRecMeta(null);
                      setRecItems([]);
                      setRecError(null);
                    }}
                    startIcon={<ClearIcon />}
                    sx={filtroButtonSecondaryStyles}
                  >
                    Limpiar
                  </AppButton>
                  <AppButton
                    dsVariant="primary"
                    dsSize="sm"
                    onClick={() => void aplicarFiltroRecorrido()}
                    startIcon={<SearchIcon />}
                    sx={filtroButtonPrimaryStyles}
                  >
                    Filtrar
                  </AppButton>
                </Box>
              </Box>
              {recError && (
                <Alert severity="error" sx={alertBaseStyles}>
                  {recError}
                </Alert>
              )}
              {!recFilterApplied ? (
                <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, py: 1 }}>
                  Usá búsqueda específica o elegí un período y tocá <strong>Filtrar</strong> para cargar el listado.
                </Typography>
              ) : recLoading ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                  <CircularProgress sx={{ color: COLORS.primary }} />
                </Box>
              ) : (
                <>
                  {recMeta && (
                    <Box sx={metaInfoStyles}>
                      <Typography sx={metaItemStyles}>
                        <strong>Total:</strong> {recMeta.total}
                      </Typography>
                      <Typography sx={metaItemStyles}>
                        <strong>Mostrando:</strong> {recItems.length} de {recMeta.total}
                      </Typography>
                      <Typography sx={metaItemStyles}>
                        <strong>Página:</strong> 1
                      </Typography>
                      {recAppliedPayload?.period.kind === "global" ? (
                        <Typography sx={metaItemStyles}>
                          <strong>Período:</strong> búsqueda global (sin rango)
                        </Typography>
                      ) : (
                        recMeta.desde &&
                        recMeta.hasta && (
                          <Typography sx={metaItemStyles}>
                            <strong>Rango:</strong> {recMeta.desde} — {recMeta.hasta}
                          </Typography>
                        )
                      )}
                    </Box>
                  )}
                  <Box sx={{ width: "100%", minWidth: 0, maxWidth: "100%" }}>
                    <MaterialReactTable table={tableRec} />
                  </Box>
                </>
              )}
            </>
          )}
        </Box>

      <ExportDataDialog
        open={exportOpen}
        onClose={() => {
          if (exportLoading) return;
          setExportOpen(false);
        }}
        title="Exportar datos"
        subtitle="Actas de comprobación"
        loading={exportLoading}
        error={exportError}
        onClearError={() => setExportError(null)}
        onExport={handleExportComprobaciones}
      />

      <ComprobacionExpedienteOperativoDialog
        open={modalExpOpen}
        onClose={closeModalExp}
        row={selectedExp}
        expNumero={expNumeroForm}
        onExpNumeroChange={setExpNumeroForm}
        expFecha={expFechaForm}
        onExpFechaChange={setExpFechaForm}
        modalApiError={modalExpError}
        saving={savingExp}
        onGuardar={handleSaveExpediente}
      />

      <ComprobacionOficioOperativoDialog
        open={modalOficioOpen}
        onClose={closeModalOficio}
        row={selectedOficio}
        juzgados={juzgados}
        documental={modalDoc}
        documentalLoading={modalDocLoading}
        documentalError={modalDocError}
        oficios={modalOficios}
        oficiosLoading={modalOficiosLoading}
        oficiosError={modalOficiosError}
        onDocumentalUpdated={reloadOficioModalDocumental}
        defaultFechaAlta={defaultRange.hasta}
        modalApiError={modalOficioError}
        modalFieldErrors={modalOficioFieldErrors}
        saving={savingOficio}
        onGuardarAlta={handleSaveOficio}
      />

      <ComprobacionReinspeccionDetalleDialog
        open={modalReinOpen}
        onClose={closeModalRein}
        row={selectedRein}
        juzgados={juzgados}
        defaultFechaAlta={defaultRange.hasta}
        onBandejasActualizadas={onReinBandejasActualizadas}
      />

      <RecorridoDetalleDocumentalDialog
        open={detalleOpen}
        onClose={() => {
          setDetalleOpen(false);
          setDetalle(null);
          setDetalleActuacionId(null);
          setDetalleListRow(null);
        }}
        actuacionId={detalleActuacionId}
        listRow={detalleListRow}
        detalle={detalle}
        loading={detalleLoading}
        juzgados={juzgados}
        defaultFechaAlta={defaultRange.hasta}
        onBandejasActualizadas={async () => {
          await onReinBandejasActualizadas();
          if (detalleActuacionId != null) {
            await reloadRecorridoDetalle(detalleActuacionId);
          }
          if (recFilterApplied && recAppliedPayload) {
            await loadRecorridoSearch(recAppliedPayload);
          }
        }}
      />
    </Box>
  );
};

export default ActasComprobacionPage;
