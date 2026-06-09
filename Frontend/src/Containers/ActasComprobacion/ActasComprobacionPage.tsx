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
  CircularProgress,
  IconButton,
  Paper,
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
  getJuzgadosCatalogo,
  type IActuacionesPendientesItem,
  type IComprobacionDocumentalResponse,
  type ICreateExpedienteRequest,
  type IJuzgadoCatalogItem,
  type IPendientesOficioItem,
  type OficioComprobacionItem,
} from "../../api/actuacionesPendientesApi";
import {
  fetchComprobacionPendientesOficio,
  fetchComprobacionRecorrido,
  fetchComprobacionRecorridoDetalle,
  fetchPendientesReinspeccionOficio,
  type IComprobacionRecorridoDetalle,
  type IComprobacionRecorridoListParams,
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

function recOficioNumCompact(r: IComprobacionRecorridoRow): string {
  const n = (r.oficio_numero ?? "").toString().trim();
  const a = r.oficio_anio != null ? String(r.oficio_anio) : "";
  if (!n && !a) return "—";
  return [n, a].filter(Boolean).join("/");
}

function recExpedienteRespuestaOficioCompact(r: IComprobacionRecorridoRow): string {
  const num = (r.expediente_respuesta_numero ?? "").toString().trim();
  const an = r.expediente_respuesta_anio != null ? String(r.expediente_respuesta_anio) : "";
  if (!num && !an) return "—";
  return [num, an].filter(Boolean).join("/");
}

/** Chips: acta, oficio, expediente de respuesta del oficio, motivo. */
function recCompOficioExpMotivoChips(r: IComprobacionRecorridoRow): string[] {
  const n = (r.acta_comprobacion_num ?? "").toString().trim();
  const comp = n ? `Comp. ${n}` : "Comp. —";
  const on = recOficioNumCompact(r);
  const ofi = on !== "—" ? `Oficio ${on}` : "Oficio —";
  const ex = recExpedienteRespuestaOficioCompact(r);
  const exp = ex !== "—" ? `Exp. oficio ${ex}` : "Exp. oficio —";
  const inf = (r.comprobacion_motivo ?? "").toString().trim();
  return [comp, ofi, exp, inf || "Sin infracción o motivo cargado"];
}

function recCompOficioExpMotivoSortKey(r: IComprobacionRecorridoRow): string {
  return recCompOficioExpMotivoChips(r).join(" | ");
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

function yearOptions(center: number): { value: string; label: string }[] {
  const out: { value: string; label: string }[] = [];
  for (let y = center - 5; y <= center + 2; y++) out.push({ value: String(y), label: String(y) });
  return out;
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
  const loadExpediente = useCallback(async () => {
    setExpLoading(true);
    setExpError(null);
    try {
      const resp = await getActuacionesPendientesExpediente(undefined, undefined, "comprobacion", null, {
        omitirRangoFecha: true,
      });
      setExpItems(resp.items);
      setExpTotalPendientes(resp.meta.total);
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
      await loadExpediente();
      await loadOficio();
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
  const [modalDoc, setModalDoc] = useState<IComprobacionDocumentalResponse | null>(null);
  const [modalDocLoading, setModalDocLoading] = useState(false);
  const [modalDocError, setModalDocError] = useState<string | null>(null);
  const [modalOficios, setModalOficios] = useState<OficioComprobacionItem[]>([]);
  const [modalOficiosLoading, setModalOficiosLoading] = useState(false);
  const [modalOficiosError, setModalOficiosError] = useState<string | null>(null);

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

  const loadOficio = useCallback(async () => {
    setOficioLoading(true);
    setOficioError(null);
    try {
      const jz = await getJuzgadosCatalogo();
      setJuzgados(jz);
      const resp = await fetchComprobacionPendientesOficio(null, null, null, { omitirRangoFecha: true });
      setOficioApiTotal(resp.meta.total);
      setOficioItems(resp.items);
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
      try {
        const doc = await fetchComprobacionDocumental(row.id);
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

  const loadRein = useCallback(async () => {
    setReinLoading(true);
    setReinError(null);
    try {
      const jz = await getJuzgadosCatalogo();
      setJuzgados(jz);
      const resp = await fetchPendientesReinspeccionOficio(null, null, null, { omitirRangoFecha: true });
      setReinApiTotal(resp.meta.total);
      setReinItems(resp.items);
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setReinError(detail || "Error al cargar pendientes de reinspección");
      setReinItems([]);
      setReinApiTotal(0);
    } finally {
      setReinLoading(false);
    }
  }, []);

  const onReinBandejasActualizadas = useCallback(async () => {
    await loadRein();
  }, [loadRein]);

  const selectedReinKey = selectedRein != null ? reinBandejaRowKey(selectedRein) : null;
  useEffect(() => {
    if (!modalReinOpen || selectedReinKey == null) return;
    const found = reinItems.find((r) => reinBandejaRowKey(r) === selectedReinKey);
    if (found) setSelectedRein(found as ReinspeccionOperativoDetalleRow);
  }, [reinItems, modalReinOpen, selectedReinKey]);

  const reloadOficioModalDocumental = useCallback(async () => {
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
    await Promise.all([loadExpediente(), loadOficio(), loadRein()]);
  }, [selectedOficio, loadExpediente, loadOficio, loadRein, loadOficiosForComprobacion]);

  const handleSaveOficio = useCallback(
    async (payload: ComprobacionOficioAltaPayload) => {
      if (!selectedOficio) return;
      if (
        !payload.numero_oficio.trim() ||
        !payload.fecha_oficio ||
        !payload.juzgado_id ||
        !payload.numero_expediente_oficio.trim()
      ) {
        setModalOficioError("Completá número/fecha/juzgado y datos del expediente de oficio");
        return;
      }
      setSavingOficio(true);
      setModalOficioError(null);
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
        await reloadOficioModalDocumental();
        await loadOficio();
        await loadRein();
      } catch (err: unknown) {
        const parsed = parseApiError(err, "No se pudo cargar el oficio");
        setModalOficioError(parsed.message);
      } finally {
        setSavingOficio(false);
      }
    },
    [selectedOficio, loadOficio, loadRein, reloadOficioModalDocumental, feedback]
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
        id: "accion_rein",
        header: "Acción",
        size: 128,
        grow: false,
        enableResizing: false,
        enableSorting: false,
        Cell: ({ row }) => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModalRein(row.original)}>
            Ver detalle
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
  const [recMes, setRecMes] = useState(defaultMonthYear.mes);
  const [recAnio, setRecAnio] = useState(defaultMonthYear.anio);
  const [recDesde, setRecDesde] = useState<string | null>(defaultRange.desde);
  const [recHasta, setRecHasta] = useState<string | null>(defaultRange.hasta);
  const [recDistritoId, setRecDistritoId] = useState<number | "">("");
  const [recContrib, setRecContrib] = useState("");
  const [recCalle, setRecCalle] = useState("");
  const [recActa, setRecActa] = useState("");
  const [recOfi, setRecOfi] = useState("");
  const [recTipoFinal, setRecTipoFinal] = useState("");
  const [recItems, setRecItems] = useState<IComprobacionRecorridoRow[]>([]);
  const [recFilterApplied, setRecFilterApplied] = useState(false);
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

  const recPeriodParams = useCallback((): IComprobacionRecorridoListParams => {
    const p: IComprobacionRecorridoListParams = {
      distrito_id: recDistritoId === "" ? undefined : recDistritoId,
    };
    if (recPeriodMode === "month") {
      p.mes = recMes;
      p.anio = recAnio;
    } else {
      p.desde = recDesde ?? undefined;
      p.hasta = recHasta ?? undefined;
    }
    return p;
  }, [recPeriodMode, recMes, recAnio, recDesde, recHasta, recDistritoId]);

  const loadRecorridoSearch = useCallback(async () => {
    setRecLoading(true);
    setRecError(null);
    try {
      const resp = await fetchComprobacionRecorrido({
        ...recPeriodParams(),
        contrib_q: recContrib.trim() || undefined,
        calle_q: recCalle.trim() || undefined,
        acta_comprobacion: recActa.trim() || undefined,
        oficio_numero: recOfi.trim() || undefined,
        tipo_final: recTipoFinal || undefined,
      });
      setRecItems(resp.items as IComprobacionRecorridoRow[]);
      setRecMeta({
        total: resp.meta.total,
        desde: resp.meta.desde,
        hasta: resp.meta.hasta,
      });
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setRecError(detail || "Error al cargar recorrido");
      setRecItems([]);
      setRecMeta(null);
    } finally {
      setRecLoading(false);
    }
  }, [recPeriodParams, recContrib, recCalle, recActa, recOfi, recTipoFinal]);

  const aplicarFiltroRecorrido = useCallback(() => {
    setRecFilterApplied(true);
    void loadRecorridoSearch();
  }, [loadRecorridoSearch]);

  useEffect(() => {
    void loadOficio();
  }, [loadOficio]);

  useEffect(() => {
    if (tab === "expediente") void loadExpediente();
    else if (tab === "oficio") void loadOficio();
    else if (tab === "reinspeccion") void loadRein();
    // Recorrido: no cargar listado al cambiar de pestaña; solo tras "Filtrar".
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carga al cambiar de pestaña (no re-disparar al editar filtros)
  }, [tab]);

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
        accessorKey: "estado_recorrido",
        header: "Recorrido",
        size: 176,
        Cell: ({ cell }) => <BandejaEllipsisCell value={String(cell.getValue() ?? "").trim() || "—"} />,
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
          tab === "recorrido" && recFilterApplied
            ? {
                distritoId: recDistritoId === "" ? null : recDistritoId,
                contribuyenteQ: recContrib.trim() || null,
                calleQ: recCalle.trim() || null,
                actaComprobacion: recActa.trim() || null,
                oficioNumero: recOfi.trim() || null,
                tipoFinal: recTipoFinal || null,
              }
            : tab === "recorrido" && recDistritoId !== ""
              ? { distritoId: recDistritoId }
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
    [
      feedback,
      tab,
      recFilterApplied,
      recDistritoId,
      recContrib,
      recCalle,
      recActa,
      recOfi,
      recTipoFinal,
    ]
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
          </Paper>

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
                          value={String(recMes)}
                          onChange={(e) => setRecMes(Number(e.target.value))}
                          variant="outlined"
                          options={MESES_OPTS}
                        />
                      </Box>
                      <Box sx={filtroItemStyles}>
                        <AppSelect
                          appearance="dense"
                          fullWidth
                          label="Año"
                          value={String(recAnio)}
                          onChange={(e) => setRecAnio(Number(e.target.value))}
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
                      label="Nº oficio (texto)"
                      value={recOfi}
                      onChange={(e) => setRecOfi(e.target.value)}
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
                <Box sx={filtroButtonsStyles}>
                  <AppButton
                    dsVariant="ghost"
                    dsSize="sm"
                    onClick={() => {
                      const r = getCurrentMonthRange();
                      const d = new Date(`${r.desde}T12:00:00`);
                      setRecPeriodMode("month");
                      setRecMes(d.getMonth() + 1);
                      setRecAnio(d.getFullYear());
                      setRecDesde(r.desde);
                      setRecHasta(r.hasta);
                      setRecDistritoId("");
                      setRecContrib("");
                      setRecCalle("");
                      setRecActa("");
                      setRecOfi("");
                      setRecTipoFinal("");
                      setRecFilterApplied(false);
                      setRecMeta(null);
                      setRecItems([]);
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
                  Tocá <strong>Filtrar</strong> para cargar el listado en la tabla (p. ej. después de <strong>Limpiar</strong> o
                  al entrar por primera vez a esta pestaña).
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
                      {recMeta.desde && recMeta.hasta && (
                        <Typography sx={metaItemStyles}>
                          <strong>Rango:</strong> {recMeta.desde} — {recMeta.hasta}
                        </Typography>
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
      />
    </Box>
  );
};

export default ActasComprobacionPage;
