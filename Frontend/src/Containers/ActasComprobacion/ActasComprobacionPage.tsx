import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import ClearIcon from "@mui/icons-material/Clear";
import SearchIcon from "@mui/icons-material/Search";
import { Alert, Box, CircularProgress, Paper, Stack, Tab, Tabs, Typography } from "@mui/material";
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
import { AppButton, AppDialog, AppSelect, AppTextField, SegmentedFilterChips } from "../../ui";
import { GLASS_COLORS, glassSecondaryTabsSx, glassTabsSecondaryPanelBarSx } from "../../styles/GlassStyles";
import { fetchDistritosCatalogo, type DistritoCatalogoItem } from "../../api/geolocalizacionApi";

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
  { value: "CUMPLE", label: "CUMPLE" },
  { value: "NO_CUMPLE", label: "NO_CUMPLE" },
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

function DetalleBloque({ titulo, data }: { titulo: string; data: Record<string, unknown> | null | undefined }) {
  return (
    <Box sx={{ borderBottom: "1px solid rgba(255,255,255,0.08)", pb: 1.5, mb: 1.5 }}>
      <Typography variant="subtitle2" sx={{ color: "rgba(255,255,255,0.9)", mb: 1 }}>
        {titulo}
      </Typography>
      {!data || Object.keys(data).length === 0 ? (
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.45)" }}>
          Sin datos
        </Typography>
      ) : (
        <Stack spacing={0.35}>
          {Object.entries(data).map(([k, v]) => (
            <Typography key={k} variant="body2" sx={{ color: "rgba(255,255,255,0.82)" }}>
              <Box component="span" sx={{ color: "rgba(255,255,255,0.5)", mr: 0.75 }}>
                {k}
              </Box>
              {v === null || v === undefined ? "—" : String(v)}
            </Typography>
          ))}
        </Stack>
      )}
    </Box>
  );
}

/**
 * Actas de comprobación: cuatro slices (expediente → oficio → reinspección → recorrido consultivo).
 */
const ActasComprobacionPage = () => {
  const navigate = useNavigate();
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
  const [expNumeroForm, setExpNumeroForm] = useState("");
  const [expFechaForm, setExpFechaForm] = useState(defaultRange.hasta);
  const [savingExp, setSavingExp] = useState(false);
  /** Tabla solo tras tocar el indicador superior (mismo patrón que Gestión de notificación / domicilios). */
  const [expTablaVisible, setExpTablaVisible] = useState(false);

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

  useEffect(() => {
    setExpTablaVisible(false);
  }, [tab]);

  const openModalExp = useCallback(
    (row: IActuacionesPendientesItem) => {
      setSelectedExp(row);
      setExpNumeroForm("");
      setExpFechaForm(defaultRange.hasta);
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
      setExpError("Completá número y fecha del expediente de comprobación");
      return;
    }
    setSavingExp(true);
    setExpError(null);
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
      setExpError(detail || "No se pudo añadir el expediente");
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

  const tableExpediente = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns: columnsExpediente,
    data: expItems,
    enableEditing: false,
    enableRowSelection: false,
  });

  // —— Pendientes de oficio
  const [oficioDesde, setOficioDesde] = useState(defaultRange.desde);
  const [oficioHasta, setOficioHasta] = useState(defaultRange.hasta);
  const [oficioActaQ, setOficioActaQ] = useState("");
  const [oficioFilterApplied, setOficioFilterApplied] = useState(false);
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

  const loadOficio = useCallback(async () => {
    setOficioLoading(true);
    setOficioError(null);
    try {
      const jz = await getJuzgadosCatalogo();
      setJuzgados(jz);
      const resp = await fetchComprobacionPendientesOficio(oficioDesde, oficioHasta, null);
      let items = resp.items;
      const q = oficioActaQ.trim().toLowerCase();
      if (q) {
        items = items.filter((r) => (r.acta_comprobacion_num || "").toLowerCase().includes(q));
      }
      setOficioApiTotal(resp.meta.total);
      setOficioItems(items);
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setOficioError(detail || "Error al cargar pendientes de oficio");
      setOficioItems([]);
      setOficioApiTotal(0);
    } finally {
      setOficioLoading(false);
    }
  }, [oficioDesde, oficioHasta, oficioActaQ]);

  const aplicarFiltroOficio = useCallback(() => {
    setOficioFilterApplied(true);
    void loadOficio();
  }, [loadOficio]);

  const openModalOficio = (row: IPendientesOficioItem) => {
    setSelectedOficio(row);
    setNumeroOficio("");
    setFechaOficio(defaultRange.hasta);
    setJuzgadoId("");
    setCausa("");
    setExpNumero("");
    setExpFecha(defaultRange.hasta);
    setModalOficioOpen(true);
  };

  const closeModalOficio = () => {
    if (savingOficio) return;
    setModalOficioOpen(false);
    setSelectedOficio(null);
  };

  const handleSaveOficio = async () => {
    if (!selectedOficio) return;
    if (!numeroOficio.trim() || !fechaOficio || !juzgadoId || !expNumero.trim() || !expFecha) {
      setOficioError("Completá número/fecha/juzgado y datos del expediente de oficio");
      return;
    }
    setSavingOficio(true);
    setOficioError(null);
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
      setOficioError(detail || "No se pudo cargar el oficio");
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
        accessorFn: () => "Esperando oficio",
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
    []
  );

  const tableOficio = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns: columnsOficio,
    data: oficioItems,
    enableEditing: false,
    enableRowSelection: false,
  });

  // —— Reinspección
  const [reinDesde, setReinDesde] = useState(defaultRange.desde);
  const [reinHasta, setReinHasta] = useState(defaultRange.hasta);
  const [reinActaQ, setReinActaQ] = useState("");
  const [reinOficioQ, setReinOficioQ] = useState("");
  const [reinFilterApplied, setReinFilterApplied] = useState(false);
  const [reinApiTotal, setReinApiTotal] = useState(0);
  const [reinItems, setReinItems] = useState<IReinspeccionOficioPendienteRow[]>([]);
  const [reinLoading, setReinLoading] = useState(false);
  const [reinError, setReinError] = useState<string | null>(null);

  const loadRein = useCallback(async () => {
    setReinLoading(true);
    setReinError(null);
    try {
      const resp = await fetchPendientesReinspeccionOficio(reinDesde, reinHasta, null);
      let items = resp.items;
      const qa = reinActaQ.trim().toLowerCase();
      if (qa) {
        items = items.filter((r) => (r.acta_comprobacion_num || "").toLowerCase().includes(qa));
      }
      const qo = reinOficioQ.trim().toLowerCase();
      if (qo) {
        items = items.filter((r) => {
          const blob = `${r.oficio_numero ?? ""}${r.oficio_anio != null ? String(r.oficio_anio) : ""}`.toLowerCase();
          return blob.includes(qo);
        });
      }
      setReinApiTotal(resp.meta.total);
      setReinItems(items);
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setReinError(detail || "Error al cargar pendientes de reinspección");
      setReinItems([]);
      setReinApiTotal(0);
    } finally {
      setReinLoading(false);
    }
  }, [reinDesde, reinHasta, reinActaQ, reinOficioQ]);

  const aplicarFiltroRein = useCallback(() => {
    setReinFilterApplied(true);
    void loadRein();
  }, [loadRein]);

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
        header: "Estado iniciador",
        size: 120,
        accessorFn: (r) => r.estado_iniciador ?? "—",
      },
      {
        id: "accion_rein",
        header: "Acción",
        size: 200,
        Cell: () => (
          <AppButton dsVariant="primary" dsSize="sm" onClick={() => navigate("/completarTrabajos")}>
            Ir a Completar trabajos
          </AppButton>
        ),
      },
    ],
    [navigate]
  );

  const tableRein = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns: columnsRein,
    data: reinItems,
    enableEditing: false,
    enableRowSelection: false,
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

  const openDetalle = async (actuacionId: number) => {
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
          <AppButton dsVariant="ghost" dsSize="sm" onClick={() => void openDetalle(row.original.id)}>
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
              <Tab label="Pendientes de expediente" />
              <Tab label="Pendientes de oficio" />
              <Tab label="Pendientes de reinspección" />
              <Tab label="Recorrido" />
            </Tabs>
          </Paper>

          {tab === "expediente" && (
            <>
              <SegmentedFilterChips
                options={[
                  {
                    value: "bandeja",
                    label: `Total pendientes · ${expLoading ? "…" : expTotalPendientes}`,
                  },
                ]}
                onSelect={() => setExpTablaVisible(true)}
                isSelected={(v) => expTablaVisible && v === "bandeja"}
                onRefresh={() => void loadExpediente()}
                refreshDisabled={expLoading}
              />
              {expError && (
                <Alert severity="error" sx={alertBaseStyles}>
                  {expError}
                </Alert>
              )}
              {expLoading && !expTablaVisible && (
                <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
                  <CircularProgress size={28} sx={{ color: COLORS.primary }} />
                </Box>
              )}
              {expTablaVisible && (
                <Box sx={{ position: "relative", opacity: expLoading ? 0.65 : 1, transition: "opacity 0.2s" }}>
                  {expLoading && (
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
              <Box sx={filtroContainerStyles}>
                <Typography sx={filtroTitleStyles}>Filtros</Typography>
                <Box sx={filtroGridStyles}>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      type="date"
                      label="Desde"
                      value={oficioDesde}
                      onChange={(e) => setOficioDesde(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      variant="outlined"
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      type="date"
                      label="Hasta"
                      value={oficioHasta}
                      onChange={(e) => setOficioHasta(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      variant="outlined"
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      label="Nº acta de comprobación (contiene)"
                      placeholder="Opcional"
                      value={oficioActaQ}
                      onChange={(e) => setOficioActaQ(e.target.value)}
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
                      setOficioDesde(r.desde);
                      setOficioHasta(r.hasta);
                      setOficioActaQ("");
                      setOficioFilterApplied(false);
                    }}
                    startIcon={<ClearIcon />}
                    sx={filtroButtonSecondaryStyles}
                  >
                    Limpiar
                  </AppButton>
                  <AppButton
                    dsVariant="primary"
                    dsSize="sm"
                    onClick={() => void aplicarFiltroOficio()}
                    startIcon={<SearchIcon />}
                    sx={filtroButtonPrimaryStyles}
                  >
                    Filtrar
                  </AppButton>
                </Box>
              </Box>
              {oficioError && (
                <Alert severity="error" sx={alertBaseStyles}>
                  {oficioError}
                </Alert>
              )}
              {!oficioFilterApplied ? (
                <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, py: 1 }}>
                  Definí el rango de fechas (y opcionalmente el nº de acta) y pulsá <strong>Filtrar</strong>.
                </Typography>
              ) : oficioLoading ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                  <CircularProgress sx={{ color: COLORS.primary }} />
                </Box>
              ) : (
                <>
                  <Box sx={metaInfoStyles}>
                    <Typography sx={metaItemStyles}>
                      <strong>Total:</strong> {oficioApiTotal}
                    </Typography>
                    <Typography sx={metaItemStyles}>
                      <strong>Mostrando:</strong> {oficioItems.length} de {oficioApiTotal}
                    </Typography>
                    <Typography sx={metaItemStyles}>
                      <strong>Página:</strong> 1
                    </Typography>
                    <Typography sx={metaItemStyles}>
                      <strong>Rango:</strong> {oficioDesde} — {oficioHasta}
                    </Typography>
                  </Box>
                  <MaterialReactTable table={tableOficio} />
                </>
              )}
            </>
          )}

          {tab === "reinspeccion" && (
            <>
              <Box sx={filtroContainerStyles}>
                <Typography sx={filtroTitleStyles}>Filtros</Typography>
                <Box sx={filtroGridStyles}>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      type="date"
                      label="Desde"
                      value={reinDesde}
                      onChange={(e) => setReinDesde(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      variant="outlined"
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      type="date"
                      label="Hasta"
                      value={reinHasta}
                      onChange={(e) => setReinHasta(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      variant="outlined"
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      label="Nº acta comprobación (contiene)"
                      placeholder="Opcional"
                      value={reinActaQ}
                      onChange={(e) => setReinActaQ(e.target.value)}
                      variant="outlined"
                    />
                  </Box>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      label="Nº oficio (contiene)"
                      placeholder="Opcional"
                      value={reinOficioQ}
                      onChange={(e) => setReinOficioQ(e.target.value)}
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
                      setReinDesde(r.desde);
                      setReinHasta(r.hasta);
                      setReinActaQ("");
                      setReinOficioQ("");
                      setReinFilterApplied(false);
                    }}
                    startIcon={<ClearIcon />}
                    sx={filtroButtonSecondaryStyles}
                  >
                    Limpiar
                  </AppButton>
                  <AppButton
                    dsVariant="primary"
                    dsSize="sm"
                    onClick={() => void aplicarFiltroRein()}
                    startIcon={<SearchIcon />}
                    sx={filtroButtonPrimaryStyles}
                  >
                    Filtrar
                  </AppButton>
                </Box>
              </Box>
              {reinError && (
                <Alert severity="error" sx={alertBaseStyles}>
                  {reinError}
                </Alert>
              )}
              {!reinFilterApplied ? (
                <Typography variant="body2" sx={{ color: GLASS_COLORS.textSecondary, py: 1 }}>
                  Definí fechas y/o criterios de acta u oficio y pulsá <strong>Filtrar</strong>.
                </Typography>
              ) : reinLoading ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                  <CircularProgress sx={{ color: COLORS.primary }} />
                </Box>
              ) : (
                <>
                  <Box sx={metaInfoStyles}>
                    <Typography sx={metaItemStyles}>
                      <strong>Total:</strong> {reinApiTotal}
                    </Typography>
                    <Typography sx={metaItemStyles}>
                      <strong>Mostrando:</strong> {reinItems.length} de {reinApiTotal}
                    </Typography>
                    <Typography sx={metaItemStyles}>
                      <strong>Página:</strong> 1
                    </Typography>
                    <Typography sx={metaItemStyles}>
                      <strong>Rango:</strong> {reinDesde} — {reinHasta}
                    </Typography>
                  </Box>
                  <MaterialReactTable table={tableRein} />
                </>
              )}
            </>
          )}

          {tab === "recorrido" && (
            <>
              <Box sx={filtroContainerStyles}>
                <Typography sx={filtroTitleStyles}>Filtros — recorrido documental</Typography>
                <Typography variant="caption" sx={{ display: "block", mb: 1.5, color: GLASS_COLORS.textMuted }}>
                  Período, distrito y criterios de texto. Pulsá <strong>Filtrar</strong> para cargar la tabla (máx. 500 por
                  consulta en servidor).
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
                  Definí período/distrito y opcionalmente criterios de texto, luego pulsá <strong>Filtrar</strong>.
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

      <AppDialog
        open={modalExpOpen}
        onClose={closeModalExp}
        title="Añadir expediente de comprobación"
        fullWidth
        maxWidth="sm"
        appearance="glass"
        onCloseButtonClick={closeModalExp}
        actions={
          <>
            <AppButton dsVariant="ghost" dsSize="sm" onClick={closeModalExp} disabled={savingExp}>
              Cancelar
            </AppButton>
            <AppButton dsVariant="primary" dsSize="sm" onClick={() => void handleSaveExpediente()} disabled={savingExp}>
              {savingExp ? "Guardando..." : "Guardar"}
            </AppButton>
          </>
        }
        contentSx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}
      >
        <AppTextField
          appearance="dense"
          label="Contexto"
          value={`Acta comp: ${selectedExp?.acta_comprobacion_num ?? "-"} | OT: ${selectedExp?.orden_trabajo_numero ?? "-"}`}
          fullWidth
          InputProps={{ readOnly: true }}
        />
        <AppTextField
          appearance="dense"
          label="Número de expediente"
          value={expNumeroForm}
          onChange={(e) => setExpNumeroForm(e.target.value)}
          fullWidth
          required
        />
        <AppTextField
          appearance="dense"
          label="Fecha de expediente"
          type="date"
          value={expFechaForm}
          onChange={(e) => setExpFechaForm(e.target.value)}
          InputLabelProps={{ shrink: true }}
          fullWidth
          required
        />
      </AppDialog>

      <AppDialog
        open={modalOficioOpen}
        onClose={closeModalOficio}
        title="Añadir oficio"
        fullWidth
        maxWidth="sm"
        appearance="glass"
        onCloseButtonClick={closeModalOficio}
        actions={
          <>
            <AppButton dsVariant="ghost" dsSize="sm" onClick={closeModalOficio} disabled={savingOficio}>
              Cancelar
            </AppButton>
            <AppButton dsVariant="primary" dsSize="sm" onClick={() => void handleSaveOficio()} disabled={savingOficio}>
              {savingOficio ? "Guardando..." : "Guardar"}
            </AppButton>
          </>
        }
        contentSx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}
      >
        <AppTextField
          appearance="dense"
          label="Expediente original"
          value={`${selectedOficio?.expediente_original_numero ?? "-"} / ${selectedOficio?.expediente_original_anio ?? "-"}`}
          fullWidth
          InputProps={{ readOnly: true }}
        />
        <AppTextField
          appearance="dense"
          label="Contexto"
          value={`Acta comp: ${selectedOficio?.acta_comprobacion_num ?? "-"} | OT: ${selectedOficio?.orden_trabajo_numero ?? "-"}`}
          fullWidth
          InputProps={{ readOnly: true }}
        />
        <AppTextField
          appearance="dense"
          label="Número de oficio"
          value={numeroOficio}
          onChange={(e) => setNumeroOficio(e.target.value)}
          fullWidth
          required
        />
        <AppTextField
          appearance="dense"
          label="Fecha de oficio"
          type="date"
          value={fechaOficio}
          onChange={(e) => setFechaOficio(e.target.value)}
          InputLabelProps={{ shrink: true }}
          fullWidth
          required
        />
        <AppSelect
          appearance="dense"
          label="Juzgado"
          value={juzgadoId === "" ? "" : String(juzgadoId)}
          onChange={(e) => setJuzgadoId(e.target.value === "" ? "" : Number(e.target.value))}
          fullWidth
          required
          variant="outlined"
          options={[{ value: "", label: "Seleccionar…" }, ...juzgados.map((j) => ({ value: String(j.id), label: j.nombre }))]}
        />
        <AppTextField appearance="dense" label="Causa" value={causa} onChange={(e) => setCausa(e.target.value)} fullWidth />
        <AppTextField
          appearance="dense"
          label="Número expediente oficio"
          value={expNumero}
          onChange={(e) => setExpNumero(e.target.value)}
          fullWidth
          required
        />
        <AppTextField
          appearance="dense"
          label="Fecha expediente oficio"
          type="date"
          value={expFecha}
          onChange={(e) => setExpFecha(e.target.value)}
          InputLabelProps={{ shrink: true }}
          fullWidth
          required
        />
      </AppDialog>

      <AppDialog
        open={detalleOpen}
        onClose={() => {
          setDetalleOpen(false);
          setDetalle(null);
          setDetalleActuacionId(null);
        }}
        onCloseButtonClick={() => {
          setDetalleOpen(false);
          setDetalle(null);
          setDetalleActuacionId(null);
        }}
        title={detalleActuacionId ? `Recorrido — actuación #${detalleActuacionId}` : "Recorrido"}
        fullWidth
        maxWidth="md"
        appearance="glass"
        actions={
          <AppButton
            dsVariant="ghost"
            dsSize="sm"
            onClick={() => {
              setDetalleOpen(false);
              setDetalle(null);
              setDetalleActuacionId(null);
            }}
          >
            Cerrar
          </AppButton>
        }
      >
        {detalleLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
            <CircularProgress sx={{ color: COLORS.primary }} />
          </Box>
        )}
        {!detalleLoading && detalle && (
          <Stack spacing={0}>
            <DetalleBloque titulo="Origen" data={detalle.origen as Record<string, unknown>} />
            <DetalleBloque titulo="Acta de comprobación" data={detalle.acta_comprobacion as Record<string, unknown>} />
            <DetalleBloque
              titulo="Expediente de comprobación"
              data={detalle.expediente_comprobacion_envio as Record<string, unknown> | null}
            />
            <DetalleBloque titulo="Oficio" data={detalle.oficio as Record<string, unknown> | null} />
            <DetalleBloque
              titulo="Expediente del oficio"
              data={detalle.expediente_respuesta_oficio as Record<string, unknown> | null}
            />
            <DetalleBloque titulo="Reinspección por oficio" data={detalle.reinspeccion_por_oficio as Record<string, unknown> | null} />
            <DetalleBloque titulo="Resultado final" data={detalle.resultado_final as Record<string, unknown>} />
          </Stack>
        )}
      </AppDialog>
    </Box>
  );
};

export default ActasComprobacionPage;
