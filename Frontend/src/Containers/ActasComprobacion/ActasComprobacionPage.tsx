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
} from "../Actuaciones/styles/filtroStyles";
import { AppButton, AppDialog, AppSelect, AppTextField } from "../../ui";
import { glassTabsSecondaryPanelSx } from "../../styles/GlassStyles";

type TabKey = "expediente" | "oficio" | "reinspeccion" | "recorrido";

function contribText(ap?: string | null, nom?: string | null): string {
  const t = [ap, nom].map((s) => (s ?? "").trim()).filter(Boolean).join(", ");
  return t || "—";
}

function domicilioText(calle?: string | null, num?: string | null): string {
  const t = [calle, num].map((s) => (s ?? "").trim()).filter(Boolean).join(" ");
  return t || "—";
}

const ESTADO_RECORRIDO_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "Esperando oficio", label: "Esperando oficio" },
  { value: "Oficio cargado — sin reinspección programada", label: "Oficio cargado — sin reinspección programada" },
  { value: "Pendiente reinspección por oficio", label: "Pendiente reinspección por oficio" },
  { value: "Reinspección cumplida", label: "Reinspección cumplida" },
];

const TIPO_FINAL_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Todos" },
  { value: "CUMPLE", label: "CUMPLE" },
  { value: "NO_CUMPLE", label: "NO_CUMPLE" },
];

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
  const [tab, setTab] = useState<TabKey>("expediente");

  // —— Pendientes de expediente (comprobación sin expediente de envío)
  const [expDesde, setExpDesde] = useState(defaultRange.desde);
  const [expHasta, setExpHasta] = useState(defaultRange.hasta);
  const [expItems, setExpItems] = useState<IActuacionesPendientesItem[]>([]);
  const [expTotal, setExpTotal] = useState(0);
  const [expLoading, setExpLoading] = useState(false);
  const [expError, setExpError] = useState<string | null>(null);
  const [selectedExp, setSelectedExp] = useState<IActuacionesPendientesItem | null>(null);
  const [modalExpOpen, setModalExpOpen] = useState(false);
  const [expNumeroForm, setExpNumeroForm] = useState("");
  const [expFechaForm, setExpFechaForm] = useState(defaultRange.hasta);
  const [savingExp, setSavingExp] = useState(false);

  const loadExpediente = useCallback(async () => {
    setExpLoading(true);
    setExpError(null);
    try {
      const resp = await getActuacionesPendientesExpediente(expDesde, expHasta, "comprobacion");
      setExpItems(resp.items);
      setExpTotal(resp.meta.total);
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setExpError(detail || "Error al cargar pendientes de expediente");
      setExpItems([]);
      setExpTotal(0);
    } finally {
      setExpLoading(false);
    }
  }, [expDesde, expHasta]);

  useEffect(() => {
    if (tab === "expediente") void loadExpediente();
  }, [tab, loadExpediente]);

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
    renderTopToolbarCustomActions: () => (
      <Typography variant="body2" sx={{ pl: 1, color: "rgba(255,255,255,0.75)" }}>
        Total pendientes de expediente: {expTotal}
      </Typography>
    ),
  });

  // —— Pendientes de oficio
  const [oficioDesde, setOficioDesde] = useState(defaultRange.desde);
  const [oficioHasta, setOficioHasta] = useState(defaultRange.hasta);
  const [oficioItems, setOficioItems] = useState<IPendientesOficioItem[]>([]);
  const [oficioTotal, setOficioTotal] = useState(0);
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
      const [resp, jz] = await Promise.all([
        fetchComprobacionPendientesOficio(oficioDesde, oficioHasta),
        getJuzgadosCatalogo(),
      ]);
      setOficioItems(resp.items);
      setOficioTotal(resp.meta.total);
      setJuzgados(jz);
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setOficioError(detail || "Error al cargar pendientes de oficio");
      setOficioItems([]);
      setOficioTotal(0);
    } finally {
      setOficioLoading(false);
    }
  }, [oficioDesde, oficioHasta]);

  useEffect(() => {
    if (tab === "oficio") void loadOficio();
  }, [tab, loadOficio]);

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
    renderTopToolbarCustomActions: () => (
      <Typography variant="body2" sx={{ pl: 1, color: "rgba(255,255,255,0.75)" }}>
        Total pendientes de oficio: {oficioTotal}
      </Typography>
    ),
  });

  // —— Reinspección
  const [reinDesde, setReinDesde] = useState(defaultRange.desde);
  const [reinHasta, setReinHasta] = useState(defaultRange.hasta);
  const [reinItems, setReinItems] = useState<IReinspeccionOficioPendienteRow[]>([]);
  const [reinLoading, setReinLoading] = useState(false);
  const [reinError, setReinError] = useState<string | null>(null);

  const loadRein = useCallback(async () => {
    setReinLoading(true);
    setReinError(null);
    try {
      const resp = await fetchPendientesReinspeccionOficio(reinDesde, reinHasta);
      setReinItems(resp.items);
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setReinError(detail || "Error al cargar pendientes de reinspección");
      setReinItems([]);
    } finally {
      setReinLoading(false);
    }
  }, [reinDesde, reinHasta]);

  useEffect(() => {
    if (tab === "reinspeccion") void loadRein();
  }, [tab, loadRein]);

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
    renderTopToolbarCustomActions: () => (
      <Typography variant="body2" sx={{ pl: 1, color: "rgba(255,255,255,0.75)" }}>
        Total pendientes de reinspección: {reinItems.length}
      </Typography>
    ),
  });

  // —— Recorrido
  const [recDesde, setRecDesde] = useState<string | null>(null);
  const [recHasta, setRecHasta] = useState<string | null>(null);
  const [recContrib, setRecContrib] = useState("");
  const [recCalle, setRecCalle] = useState("");
  const [recNumero, setRecNumero] = useState("");
  const [recActa, setRecActa] = useState("");
  const [recExp, setRecExp] = useState("");
  const [recOfi, setRecOfi] = useState("");
  const [recEstado, setRecEstado] = useState("");
  const [recTipoFinal, setRecTipoFinal] = useState("");
  const [recItems, setRecItems] = useState<IComprobacionRecorridoRow[]>([]);
  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState<string | null>(null);
  const [detalleOpen, setDetalleOpen] = useState(false);
  const [detalleLoading, setDetalleLoading] = useState(false);
  const [detalle, setDetalle] = useState<IComprobacionRecorridoDetalle | null>(null);
  const [detalleActuacionId, setDetalleActuacionId] = useState<number | null>(null);

  const loadRecorrido = useCallback(async () => {
    setRecLoading(true);
    setRecError(null);
    try {
      const resp = await fetchComprobacionRecorrido({
        desde: recDesde || undefined,
        hasta: recHasta || undefined,
        contrib_q: recContrib.trim() || undefined,
        calle_q: recCalle.trim() || undefined,
        numero_q: recNumero.trim() || undefined,
        acta_comprobacion: recActa.trim() || undefined,
        expediente_numero: recExp.trim() || undefined,
        oficio_numero: recOfi.trim() || undefined,
        estado_recorrido: recEstado || undefined,
        tipo_final: recTipoFinal || undefined,
      });
      setRecItems(resp.items as IComprobacionRecorridoRow[]);
    } catch (err: unknown) {
      const detail = err && typeof err === "object" && "response" in err ? (err as any).response?.data?.detail : null;
      setRecError(detail || "Error al cargar recorrido");
      setRecItems([]);
    } finally {
      setRecLoading(false);
    }
  }, [recDesde, recHasta, recContrib, recCalle, recNumero, recActa, recExp, recOfi, recEstado, recTipoFinal]);

  /** Al entrar al slice Recorrido se consulta una vez; los cambios de filtros aplican con «Buscar». */
  useEffect(() => {
    if (tab === "recorrido") void loadRecorrido();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- evita refetch en cada tecla de los filtros
  }, [tab]);

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
    renderTopToolbarCustomActions: () => (
      <Typography variant="body2" sx={{ pl: 1, color: "rgba(255,255,255,0.75)" }}>
        {recItems.length} registro(s) (máx. 500 por consulta)
      </Typography>
    ),
  });

  const tabIndex =
    tab === "expediente" ? 0 : tab === "oficio" ? 1 : tab === "reinspeccion" ? 2 : 3;

  return (
    <Box sx={containerStyles}>
      <Box sx={wrapperStyles}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Paper elevation={0} sx={{ ...glassTabsSecondaryPanelSx, position: "sticky", top: 0, zIndex: 2 }}>
            <Typography variant="h6" sx={{ color: "rgba(255,255,255,0.95)", mb: 1, fontWeight: 600 }}>
              Actas de comprobación
            </Typography>
            <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.55)", mb: 1.5 }}>
              Expediente → oficio → reinspección por oficio; recorrido consultivo del circuito documental.
            </Typography>
            <Tabs
              value={tabIndex}
              onChange={(_, v) => {
                setTab(
                  v === 0 ? "expediente" : v === 1 ? "oficio" : v === 2 ? "reinspeccion" : "recorrido"
                );
              }}
              sx={{
                minHeight: 40,
                "& .MuiTab-root": { color: "rgba(255,255,255,0.55)", minHeight: 40, textTransform: "none" },
                "& .Mui-selected": { color: "#fff" },
                "& .MuiTabs-indicator": { backgroundColor: COLORS.primary },
              }}
            >
              <Tab label="Pendientes de expediente" />
              <Tab label="Pendientes de oficio" />
              <Tab label="Pendientes de reinspección" />
              <Tab label="Recorrido" />
            </Tabs>
          </Paper>

          {tab === "expediente" && (
            <>
              <Box sx={filtroContainerStyles}>
                <Typography sx={filtroTitleStyles}>Filtro secundario (fecha)</Typography>
                <Box sx={filtroGridStyles}>
                  <Box sx={filtroItemStyles}>
                    <AppTextField
                      appearance="dense"
                      fullWidth
                      type="date"
                      label="Desde"
                      value={expDesde}
                      onChange={(e) => setExpDesde(e.target.value)}
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
                      value={expHasta}
                      onChange={(e) => setExpHasta(e.target.value)}
                      InputLabelProps={{ shrink: true }}
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
                      setExpDesde(r.desde);
                      setExpHasta(r.hasta);
                    }}
                    startIcon={<ClearIcon />}
                    sx={filtroButtonSecondaryStyles}
                  >
                    Limpiar
                  </AppButton>
                  <AppButton
                    dsVariant="primary"
                    dsSize="sm"
                    onClick={() => void loadExpediente()}
                    startIcon={<SearchIcon />}
                    sx={filtroButtonPrimaryStyles}
                  >
                    Filtrar
                  </AppButton>
                </Box>
              </Box>
              {expError && (
                <Alert severity="error" sx={alertBaseStyles}>
                  {expError}
                </Alert>
              )}
              {expLoading ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                  <CircularProgress sx={{ color: COLORS.primary }} />
                </Box>
              ) : (
                <MaterialReactTable table={tableExpediente} />
              )}
            </>
          )}

          {tab === "oficio" && (
            <>
              <Box sx={filtroContainerStyles}>
                <Typography sx={filtroTitleStyles}>Filtro secundario (fecha)</Typography>
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
                </Box>
                <Box sx={filtroButtonsStyles}>
                  <AppButton
                    dsVariant="ghost"
                    dsSize="sm"
                    onClick={() => {
                      const r = getCurrentMonthRange();
                      setOficioDesde(r.desde);
                      setOficioHasta(r.hasta);
                    }}
                    startIcon={<ClearIcon />}
                    sx={filtroButtonSecondaryStyles}
                  >
                    Limpiar
                  </AppButton>
                  <AppButton
                    dsVariant="primary"
                    dsSize="sm"
                    onClick={() => void loadOficio()}
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
              {oficioLoading ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                  <CircularProgress sx={{ color: COLORS.primary }} />
                </Box>
              ) : (
                <MaterialReactTable table={tableOficio} />
              )}
            </>
          )}

          {tab === "reinspeccion" && (
            <>
              <Box sx={filtroContainerStyles}>
                <Typography sx={filtroTitleStyles}>Filtro secundario (fecha sobre actuación)</Typography>
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
                </Box>
                <Box sx={filtroButtonsStyles}>
                  <AppButton
                    dsVariant="ghost"
                    dsSize="sm"
                    onClick={() => {
                      const r = getCurrentMonthRange();
                      setReinDesde(r.desde);
                      setReinHasta(r.hasta);
                    }}
                    startIcon={<ClearIcon />}
                    sx={filtroButtonSecondaryStyles}
                  >
                    Limpiar
                  </AppButton>
                  <AppButton
                    dsVariant="primary"
                    dsSize="sm"
                    onClick={() => void loadRein()}
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
              {reinLoading ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                  <CircularProgress sx={{ color: COLORS.primary }} />
                </Box>
              ) : (
                <MaterialReactTable table={tableRein} />
              )}
            </>
          )}

          {tab === "recorrido" && (
            <>
              <Box sx={filtroContainerStyles}>
                <Typography sx={filtroTitleStyles}>Consulta — recorrido documental</Typography>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" },
                    gap: 1.5,
                  }}
                >
                  <AppTextField
                    appearance="dense"
                    label="Desde"
                    type="date"
                    value={recDesde ?? ""}
                    onChange={(e) => setRecDesde(e.target.value || null)}
                    InputLabelProps={{ shrink: true }}
                    fullWidth
                  />
                  <AppTextField
                    appearance="dense"
                    label="Hasta"
                    type="date"
                    value={recHasta ?? ""}
                    onChange={(e) => setRecHasta(e.target.value || null)}
                    InputLabelProps={{ shrink: true }}
                    fullWidth
                  />
                  <AppTextField
                    appearance="dense"
                    label="Contribuyente"
                    value={recContrib}
                    onChange={(e) => setRecContrib(e.target.value)}
                    fullWidth
                  />
                  <AppTextField
                    appearance="dense"
                    label="Calle"
                    value={recCalle}
                    onChange={(e) => setRecCalle(e.target.value)}
                    fullWidth
                  />
                  <AppTextField
                    appearance="dense"
                    label="Número"
                    value={recNumero}
                    onChange={(e) => setRecNumero(e.target.value)}
                    fullWidth
                  />
                  <AppTextField
                    appearance="dense"
                    label="Nº comprobación"
                    value={recActa}
                    onChange={(e) => setRecActa(e.target.value)}
                    fullWidth
                  />
                  <AppTextField
                    appearance="dense"
                    label="Nº expediente (texto)"
                    value={recExp}
                    onChange={(e) => setRecExp(e.target.value)}
                    fullWidth
                  />
                  <AppTextField
                    appearance="dense"
                    label="Nº oficio (texto)"
                    value={recOfi}
                    onChange={(e) => setRecOfi(e.target.value)}
                    fullWidth
                  />
                  <AppSelect
                    appearance="dense"
                    label="Estado del recorrido"
                    value={recEstado}
                    onChange={(e) => setRecEstado(String(e.target.value))}
                    fullWidth
                    options={ESTADO_RECORRIDO_FILTER_OPTIONS}
                  />
                  <AppSelect
                    appearance="dense"
                    label="Tipo final (resultado)"
                    value={recTipoFinal}
                    onChange={(e) => setRecTipoFinal(String(e.target.value))}
                    fullWidth
                    options={TIPO_FINAL_OPTIONS}
                  />
                </Box>
                <Box sx={{ ...filtroButtonsStyles, mt: 1.5 }}>
                  <AppButton
                    dsVariant="ghost"
                    dsSize="sm"
                    onClick={() => {
                      setRecDesde(null);
                      setRecHasta(null);
                      setRecContrib("");
                      setRecCalle("");
                      setRecNumero("");
                      setRecActa("");
                      setRecExp("");
                      setRecOfi("");
                      setRecEstado("");
                      setRecTipoFinal("");
                    }}
                    startIcon={<ClearIcon />}
                    sx={filtroButtonSecondaryStyles}
                  >
                    Limpiar
                  </AppButton>
                  <AppButton
                    dsVariant="primary"
                    dsSize="sm"
                    onClick={() => void loadRecorrido()}
                    startIcon={<SearchIcon />}
                    sx={filtroButtonPrimaryStyles}
                  >
                    Buscar
                  </AppButton>
                </Box>
              </Box>
              {recError && (
                <Alert severity="error" sx={alertBaseStyles}>
                  {recError}
                </Alert>
              )}
              {recLoading ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                  <CircularProgress sx={{ color: COLORS.primary }} />
                </Box>
              ) : (
                <MaterialReactTable table={tableRec} />
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
