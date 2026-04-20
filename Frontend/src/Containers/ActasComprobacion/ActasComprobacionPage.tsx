import { useCallback, useEffect, useMemo, useState } from "react";
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
import { MaterialReactTable, useMaterialReactTable, type MRT_ColumnDef } from "material-react-table";

import {
  createExpedienteDesdeActuacion,
  createOficioDesdeActuacion,
  getActuacionesPendientesExpediente,
  getJuzgadosCatalogo,
  type IActuacionesPendientesItem,
  type ICreateExpedienteRequest,
  type IJuzgadoCatalogItem,
  type IPendientesOficioItem,
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
import { containerStyles, wrapperStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";
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
import { AppButton, AppSelect, AppTextField } from "../../ui";
import { humanizarEstadoIniciador } from "./utils/documentalLabelFormat";
import { GLASS_COLORS, glassSecondaryTabsSx, glassTabsSecondaryPanelBarSx } from "../../styles/GlassStyles";
import { fetchDistritosCatalogo, type DistritoCatalogoItem } from "../../api/geolocalizacionApi";
import { ComprobacionExpedienteOperativoDialog } from "./components/ComprobacionExpedienteOperativoDialog";
import { ComprobacionOficioOperativoDialog } from "./components/ComprobacionOficioOperativoDialog";
import { ComprobacionReinspeccionDetalleDialog } from "./components/ComprobacionReinspeccionDetalleDialog";
import type { ReinspeccionOperativoDetalleRow } from "./components/comprobacionOperativoBlocks";
import { RecorridoDetalleDocumentalDialog } from "./components/RecorridoDetalleDocumentalDialog";

type TabKey = "expediente" | "oficio" | "reinspeccion" | "recorrido";

/** Evita recortes: `wrapperStyles` usa height 91% y rompe el scroll del layout con muchos filtros (p. ej. Recorrido). */
const actasPageWrapperSx = {
  ...wrapperStyles,
  height: "auto" as const,
  minHeight: "100%",
  width: "100%",
  maxWidth: "100%",
  boxSizing: "border-box" as const,
};

const actasContentColumnSx = {
  ...moduleContentColumnSx,
  width: "100%",
  maxWidth: "100%",
  minWidth: 0,
};

type RecPeriodMode = "month" | "range";

function contribText(ap?: string | null, nom?: string | null): string {
  const t = [ap, nom].map((s) => (s ?? "").trim()).filter(Boolean).join(", ");
  return t || "—";
}

function domicilioText(calle?: string | null, num?: string | null): string {
  const t = [calle, num].map((s) => (s ?? "").trim()).filter(Boolean).join(" ");
  return t || "—";
}

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
  const defaultRange = useMemo(() => getCurrentMonthRange(), []);
  const defaultMonthYear = useMemo(() => {
    const d = new Date(`${defaultRange.desde}T12:00:00`);
    return { mes: d.getMonth() + 1, anio: d.getFullYear() };
  }, [defaultRange.desde]);
  const [tab, setTab] = useState<TabKey>("expediente");
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

  useEffect(() => {
    if (tab === "expediente") void loadExpediente();
  }, [tab, loadExpediente]);

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
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setModalExpError(detail || "No se pudo añadir el expediente");
    } finally {
      setSavingExp(false);
    }
  };

  const columnsExpediente = useMemo<MRT_ColumnDef<IActuacionesPendientesItem>[]>(
    () => [
      { accessorKey: "fecha_actuacion", header: "Fecha", size: 110 },
      { accessorKey: "orden_trabajo_numero", header: "OT", size: 110 },
      {
        id: "contrib",
        header: "Contribuyente",
        size: 180,
        accessorFn: (r) => contribText(r.contrib_apellido, r.contrib_nombre),
      },
      {
        id: "domicilio",
        header: "Domicilio",
        size: 200,
        accessorFn: (r) => domicilioText(r.calle, r.numero),
      },
      { accessorKey: "rubro_nombre", header: "Rubro", size: 140 },
      { accessorKey: "acta_comprobacion_num", header: "Nº comprobación", size: 130 },
      {
        id: "acciones",
        header: "Acción",
        size: 160,
        Cell: ({ row }) => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModalExp(row.original)}>
            Añadir expediente
          </AppButton>
        ),
      },
    ],
    [openModalExp]
  );

  const renderExpedienteToolbarRefresh = useCallback(
    () => (
      <Tooltip title="Actualizar listado">
        <span>
          <IconButton
            type="button"
            size="small"
            aria-label="Actualizar listado"
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
  const [selectedOficio, setSelectedOficio] = useState<IPendientesOficioItem | null>(null);
  const [modalOficioOpen, setModalOficioOpen] = useState(false);
  const [numeroOficio, setNumeroOficio] = useState("");
  const [fechaOficio, setFechaOficio] = useState(defaultRange.hasta);
  const [juzgadoId, setJuzgadoId] = useState<number | "">("");
  const [causa, setCausa] = useState("");
  const [expNumero, setExpNumero] = useState("");
  const [expFecha, setExpFecha] = useState(defaultRange.hasta);
  const [savingOficio, setSavingOficio] = useState(false);
  const [modalOficioError, setModalOficioError] = useState<string | null>(null);

  const loadOficio = useCallback(async () => {
    setOficioLoading(true);
    setOficioError(null);
    try {
      const jz = await getJuzgadosCatalogo();
      setJuzgados(jz);
      const r = getCurrentMonthRange();
      const resp = await fetchComprobacionPendientesOficio(r.desde, r.hasta, null);
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

  const openModalOficio = useCallback((row: IPendientesOficioItem) => {
    setSelectedOficio(row);
    setNumeroOficio("");
    setFechaOficio(defaultRange.hasta);
    setJuzgadoId("");
    setCausa("");
    setExpNumero("");
    setExpFecha(defaultRange.hasta);
    setModalOficioError(null);
    setModalOficioOpen(true);
  }, [defaultRange.hasta]);

  const closeModalOficio = () => {
    if (savingOficio) return;
    setModalOficioOpen(false);
    setSelectedOficio(null);
  };

  const handleSaveOficio = async () => {
    if (!selectedOficio) return;
    if (!numeroOficio.trim() || !fechaOficio || !juzgadoId || !expNumero.trim() || !expFecha) {
      setModalOficioError("Completá número/fecha/juzgado y datos del expediente de oficio");
      return;
    }
    setSavingOficio(true);
    setModalOficioError(null);
    try {
      await createOficioDesdeActuacion(selectedOficio.id, {
        numero_oficio: numeroOficio.trim(),
        fecha_oficio: fechaOficio,
        juzgado_id: Number(juzgadoId),
        causa: causa.trim() || null,
        numero_expediente_oficio: expNumero.trim(),
        fecha_expediente_oficio: expFecha,
      });
      closeModalOficio();
      await loadOficio();
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setModalOficioError(detail || "No se pudo cargar el oficio");
    } finally {
      setSavingOficio(false);
    }
  };

  const columnsOficio = useMemo<MRT_ColumnDef<IPendientesOficioItem>[]>(
    () => [
      { accessorKey: "fecha_actuacion", header: "Fecha", size: 110 },
      { accessorKey: "orden_trabajo_numero", header: "OT", size: 110 },
      {
        id: "contrib",
        header: "Contribuyente",
        size: 180,
        accessorFn: (r) => contribText(r.contrib_apellido, r.contrib_nombre),
      },
      {
        id: "domicilio",
        header: "Domicilio",
        size: 200,
        accessorFn: (r) => domicilioText(r.calle, r.numero),
      },
      { accessorKey: "rubro_nombre", header: "Rubro", size: 140 },
      { accessorKey: "acta_comprobacion_num", header: "Nº comprobación", size: 130 },
      {
        id: "estado_doc",
        header: "Estado / documento pendiente",
        size: 200,
        accessorFn: () => "Pendiente de oficio (carga manual)",
      },
      {
        id: "acciones",
        header: "Acción",
        size: 150,
        Cell: ({ row }) => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => openModalOficio(row.original)}>
            Añadir oficio
          </AppButton>
        ),
      },
    ],
    [openModalOficio]
  );

  const renderOficioToolbarRefresh = useCallback(
    () => (
      <Tooltip title="Actualizar listado">
        <span>
          <IconButton
            type="button"
            size="small"
            aria-label="Actualizar listado"
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
    columns: columnsOficio,
    data: oficioItems,
    enableEditing: false,
    enableRowSelection: false,
    renderTopToolbarCustomActions: renderOficioToolbarRefresh,
  });

  // —— Reinspección (siempre mes corriente; sin filtro previo a la tabla)
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
      const r = getCurrentMonthRange();
      const resp = await fetchPendientesReinspeccionOficio(r.desde, r.hasta, null);
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

  const columnsRein = useMemo<MRT_ColumnDef<IReinspeccionOficioPendienteRow>[]>(
    () => [
      { accessorKey: "fecha_actuacion", header: "Fecha", size: 110 },
      { accessorKey: "orden_trabajo_numero", header: "OT", size: 110 },
      {
        id: "contrib",
        header: "Contribuyente",
        size: 180,
        accessorFn: (r) => contribText(r.contrib_apellido, r.contrib_nombre),
      },
      {
        id: "domicilio",
        header: "Domicilio",
        size: 200,
        accessorFn: (r) => domicilioText(r.calle, r.numero),
      },
      { accessorKey: "rubro_nombre", header: "Rubro", size: 140 },
      { accessorKey: "acta_comprobacion_num", header: "Nº comprobación", size: 130 },
      {
        id: "oficio_ref",
        header: "Nº oficio",
        size: 130,
        accessorFn: (r) => {
          const n = r.oficio_numero ?? "";
          const a = r.oficio_anio != null ? String(r.oficio_anio) : "";
          const t = [n, a].filter(Boolean).join(" / ");
          return t || "—";
        },
      },
      { accessorKey: "documento_pendiente", header: "Estado / documento pendiente", size: 200 },
      {
        id: "estado_ini",
        header: "Estado del iniciador",
        size: 120,
        accessorFn: (r) => humanizarEstadoIniciador(r.estado_iniciador),
      },
      {
        id: "accion_rein",
        header: "Acción",
        size: 160,
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
      <Tooltip title="Actualizar listado">
        <span>
          <IconButton
            type="button"
            size="small"
            aria-label="Actualizar listado"
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
    columns: columnsRein,
    data: reinItems,
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
    if (tab === "oficio") void loadOficio();
    else if (tab === "reinspeccion") void loadRein();
    else if (tab === "recorrido") {
      setRecFilterApplied(true);
      void loadRecorridoSearch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carga al cambiar de pestaña (no re-disparar al editar filtros)
  }, [tab]);

  const openDetalle = async (row: IComprobacionRecorridoRow) => {
    const actuacionId = row.id;
    setDetalleListRow(row);
    setDetalleActuacionId(actuacionId);
    setDetalleOpen(true);
    setDetalleLoading(true);
    setDetalle(null);
    try {
      const d = await fetchComprobacionRecorridoDetalle(actuacionId);
      setDetalle(d);
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setRecError(detail || "No se pudo cargar el detalle");
      setDetalleOpen(false);
      setDetalleListRow(null);
    } finally {
      setDetalleLoading(false);
    }
  };

  const columnsRec = useMemo<MRT_ColumnDef<IComprobacionRecorridoRow>[]>(
    () => [
      { accessorKey: "fecha_actuacion", header: "Fecha", size: 110 },
      { accessorKey: "orden_trabajo_numero", header: "OT", size: 110 },
      {
        id: "contrib",
        header: "Contribuyente",
        size: 180,
        accessorFn: (r) => contribText(r.contrib_apellido, r.contrib_nombre),
      },
      {
        id: "domicilio",
        header: "Domicilio",
        size: 200,
        accessorFn: (r) => domicilioText(r.calle, r.numero),
      },
      { accessorKey: "rubro_nombre", header: "Rubro", size: 140 },
      { accessorKey: "acta_comprobacion_num", header: "Nº comprobación", size: 130 },
      { accessorKey: "estado_recorrido", header: "Estado del recorrido", size: 260 },
      {
        id: "ver",
        header: "Acción",
        size: 120,
        Cell: ({ row }) => (
          <AppButton dsVariant="ghost" dsSize="sm" onClick={() => void openDetalle(row.original)}>
            Ver detalle
          </AppButton>
        ),
      },
    ],
    []
  );

  const tableRec = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns: columnsRec,
    data: recItems,
    enableEditing: false,
    enableRowSelection: false,
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
        /** Mucho contenido arriba (filtros): altura fija más conservadora para no pelear con el scroll del layout */
        maxHeight: { xs: "min(45vh, 360px)", sm: "min(52vh, 440px)", md: "min(58vh, 520px)" },
      },
    },
  });

  const tabIndex =
    tab === "expediente" ? 0 : tab === "oficio" ? 1 : tab === "reinspeccion" ? 2 : 3;

  return (
    <Box sx={containerStyles}>
      <Box sx={actasPageWrapperSx}>
        <Box sx={{ ...actasContentColumnSx, gap: 2 }}>
          <Paper elevation={0} sx={{ ...glassTabsSecondaryPanelBarSx, width: "100%" }}>
            <Tabs
              value={tabIndex}
              onChange={(_, v) => {
                setTab(
                  v === 0 ? "expediente" : v === 1 ? "oficio" : v === 2 ? "reinspeccion" : "recorrido"
                );
              }}
              variant="scrollable"
              allowScrollButtonsMobile
              sx={glassSecondaryTabsSx}
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
                <Typography sx={filtroTitleStyles}>Recorrido — filtros documentales</Typography>
                <Typography variant="caption" sx={{ display: "block", color: "rgba(255,255,255,0.55)", mb: 1.5 }}>
                  Período calendario o rango de fechas, distrito y criterios opcionales por contribuyente, calle, número
                  de acta de comprobación o número de oficio. Tipo final acota por resultado del circuito. Los campos de
                  texto son opcionales. Al entrar a esta pestaña se carga el listado con el mes/año o rango elegido; tocá{" "}
                  <strong>Filtrar</strong> después de cambiar criterios (máx. 500 filas por consulta en servidor).
                </Typography>
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
                  Tocá <strong>Filtrar</strong> para volver a cargar el listado (p. ej. después de <strong>Limpiar</strong>).
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
      </Box>

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
        numeroOficio={numeroOficio}
        onNumeroOficioChange={setNumeroOficio}
        fechaOficio={fechaOficio}
        onFechaOficioChange={setFechaOficio}
        juzgadoId={juzgadoId}
        onJuzgadoIdChange={setJuzgadoId}
        causa={causa}
        onCausaChange={setCausa}
        expNumero={expNumero}
        onExpNumeroChange={setExpNumero}
        expFecha={expFecha}
        onExpFechaChange={setExpFecha}
        modalApiError={modalOficioError}
        saving={savingOficio}
        onGuardar={handleSaveOficio}
      />

      <ComprobacionReinspeccionDetalleDialog open={modalReinOpen} onClose={closeModalRein} row={selectedRein} />

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
