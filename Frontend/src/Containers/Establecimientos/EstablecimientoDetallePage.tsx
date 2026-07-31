import { useEffect, useMemo, useRef, useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import LocationOnIcon from "@mui/icons-material/LocationOn";
import StorefrontIcon from "@mui/icons-material/Storefront";
import { Alert, Box, Paper, Stack, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_PaginationState,
} from "material-react-table";
import { isAxiosError } from "axios";

import { AppButton } from "../../ui";
import { DataTableMrtShell } from "../../components/dataTable/DataTableMrtShell";
import { BANDEJA_MRT_SPINNER_LOADING_STATE, BandejaTableSpinner } from "../../components/dataTable/bandejaTableLoading";
import { COLORS } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import { DARK_TABLE_CONFIG } from "../Actuaciones/styles/actuacionesTableStyles";
import {
  BandejaEllipsisCell,
  BandejaTipoActuacionChipCell,
  BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
} from "../Actuaciones/Components/bandejaTableCells";
import { HistorialActasTramitesCell } from "./components/HistorialActasTramitesCell";
import { HistorialInspectoresCell } from "./components/HistorialInspectoresCell";
import { historialActasTramitesChipLabels } from "./utils/historialActasTramitesVisual";
import { establecimientoDomicilioLineaVisible } from "./utils/establecimientoDomicilioVisible";
import { glassCard } from "../../styles/GlassStyles";
import {
  getEstablecimientoOperativoActuaciones,
  getEstablecimientoOperativoById,
  type IEstablecimientoOperativoDetail,
  type IEstablecimientoOperativoHistorialRow,
} from "../../api/establecimientosOperativosApi";

const HIST_PAGE_SIZE = 20;

function formatFecha(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("es-AR", { dateStyle: "medium" });
}

function dash(v: string | null | undefined): string {
  const t = v?.trim();
  return t ? t : "—";
}

/**
 * Ficha de establecimiento operativo: cabecera e historial desde API (JWT vía apiClient).
 */
export default function EstablecimientoDetallePage() {
  const { id: idParam } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const establecimientoId = useMemo(() => {
    if (!idParam || !/^\d+$/.test(idParam)) return null;
    return Number.parseInt(idParam, 10);
  }, [idParam]);

  const [detalle, setDetalle] = useState<IEstablecimientoOperativoDetail | null>(null);
  const [loadingDetalle, setLoadingDetalle] = useState(false);
  const [errorDetalle, setErrorDetalle] = useState<string | null>(null);

  const [historialRows, setHistorialRows] = useState<IEstablecimientoOperativoHistorialRow[]>([]);
  /** `null` = aún no hubo respuesta para el id/pestaña actual (evita flash “sin registros” al cargar). */
  const [historialTotal, setHistorialTotal] = useState<number | null>(null);
  const [loadingHistorial, setLoadingHistorial] = useState(false);
  const [errorHistorial, setErrorHistorial] = useState<string | null>(null);
  const [pagination, setPagination] = useState<MRT_PaginationState>({
    pageIndex: 0,
    pageSize: HIST_PAGE_SIZE,
  });

  const prevHistorialEstIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (establecimientoId == null) {
      setDetalle(null);
      setErrorDetalle(null);
      return;
    }
    let cancelled = false;
    setLoadingDetalle(true);
    setErrorDetalle(null);
    void getEstablecimientoOperativoById(establecimientoId)
      .then((d) => {
        if (!cancelled) {
          setDetalle(d);
        }
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (isAxiosError(e) && e.response?.status === 404) {
          setErrorDetalle("Establecimiento operativo no encontrado.");
          setDetalle(null);
          return;
        }
        const detail =
          isAxiosError(e) && e.response?.data && typeof e.response.data === "object"
            ? (e.response.data as { detail?: string }).detail
            : null;
        setErrorDetalle(detail ?? "No se pudo cargar la ficha.");
        setDetalle(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingDetalle(false);
      });
    return () => {
      cancelled = true;
    };
  }, [establecimientoId]);

  useEffect(() => {
    if (establecimientoId == null) return;

    const idChanged = prevHistorialEstIdRef.current !== establecimientoId;
    if (idChanged) {
      prevHistorialEstIdRef.current = establecimientoId;
      setHistorialRows([]);
      setHistorialTotal(null);
      setErrorHistorial(null);
      if (pagination.pageIndex !== 0) {
        setPagination((p) => ({ ...p, pageIndex: 0 }));
      }
    }

    const effectivePageIndex = idChanged ? 0 : pagination.pageIndex;

    let cancelled = false;
    setLoadingHistorial(true);
    setErrorHistorial(null);
    void getEstablecimientoOperativoActuaciones(establecimientoId, {
      page: effectivePageIndex + 1,
      page_size: pagination.pageSize,
    })
      .then((res) => {
        if (cancelled) return;
        setHistorialRows(res.items);
        setHistorialTotal(res.meta.total);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        const detail =
          isAxiosError(e) && e.response?.data && typeof e.response.data === "object"
            ? (e.response.data as { detail?: string }).detail
            : null;
        setErrorHistorial(detail ?? "No se pudo cargar el historial de actuaciones.");
        setHistorialRows([]);
        setHistorialTotal(0);
      })
      .finally(() => {
        if (!cancelled) setLoadingHistorial(false);
      });

    return () => {
      cancelled = true;
    };
  }, [establecimientoId, pagination.pageIndex, pagination.pageSize]);

  const tituloPrincipal = useMemo(() => {
    if (!detalle) return "";
    const rs = detalle.razon_social?.trim();
    if (rs) return rs;
    const nom = [detalle.contrib_nombre, detalle.contrib_apellido].filter(Boolean).join(" ").trim();
    if (nom) return nom;
    return `Establecimiento #${detalle.id}`;
  }, [detalle]);

  const domicilioLinea = useMemo(() => {
    if (!detalle) return "";
    return establecimientoDomicilioLineaVisible(detalle);
  }, [detalle]);

  const colsHistorial = useMemo<MRT_ColumnDef<IEstablecimientoOperativoHistorialRow>[]>(
    () => [
      {
        accessorKey: "fecha",
        header: "FECHA",
        size: 130,
        Cell: ({ row }) => <BandejaEllipsisCell value={formatFecha(row.original.fecha)} />,
      },
      {
        accessorKey: "tipo_actuacion",
        header: "TIPO DE ACTUACIÓN",
        size: 200,
        accessorFn: (row) =>
          [row.tipo_actuacion ?? "", row.contraproducencia ?? ""].filter((s) => s?.trim()).join(" · "),
        Cell: ({ row }) => (
          <BandejaTipoActuacionChipCell
            tipo={row.original.tipo_actuacion}
            contraproducencia={row.original.contraproducencia}
          />
        ),
      },
      {
        accessorKey: "inspectores_texto",
        header: "INSPECTORES",
        size: 180,
        grow: true,
        Cell: ({ row }) => (
          <HistorialInspectoresCell inspectoresTexto={row.original.inspectores_texto} />
        ),
      },
      {
        id: "actas_tramites",
        header: "ACTAS Y TRÁMITES",
        size: 280,
        grow: true,
        accessorFn: (row) =>
          historialActasTramitesChipLabels(row.actas, row.tramites).join(" · ") ||
          row.actas_tramites_texto?.trim() ||
          "",
        Cell: ({ row }) => (
          <HistorialActasTramitesCell actas={row.original.actas} tramites={row.original.tramites} />
        ),
      },
    ],
    []
  );

  const tableHistorial = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
    columns: colsHistorial,
    data: historialRows,
    getRowId: (r) => String(r.id),
    enableEditing: false,
    enableRowSelection: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    manualPagination: true,
    rowCount: historialTotal ?? 0,
    state: {
      pagination,
      ...BANDEJA_MRT_SPINNER_LOADING_STATE,
    },
    onPaginationChange: setPagination,
    enableRowActions: false,
  });

  if (establecimientoId == null) {
    return (
      <Stack spacing={2} sx={{ p: 1 }}>
        <AppButton
          dsVariant="secondary"
          startIcon={<ArrowBackIcon />}
          component={RouterLink}
          to="/establecimientos"
        >
          Volver al listado
        </AppButton>
        <Typography sx={{ color: COLORS.white, fontFamily: '"Tactic Sans", sans-serif' }}>
          El identificador de la ficha no es válido. Usá el listado para abrir una ficha por su ID numérico.
        </Typography>
      </Stack>
    );
  }

  if (loadingDetalle && !detalle) {
    return (
      <Stack spacing={2} sx={{ p: 1 }}>
        <AppButton
          dsVariant="ghost"
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate("/establecimientos")}
          sx={{ color: "rgba(255,255,255,0.75)", alignSelf: "flex-start" }}
        >
          Volver
        </AppButton>
        <BandejaTableSpinner minHeight={200} />
      </Stack>
    );
  }

  if (errorDetalle || !detalle) {
    return (
      <Stack spacing={2} sx={{ p: 1 }}>
        <AppButton
          dsVariant="secondary"
          startIcon={<ArrowBackIcon />}
          component={RouterLink}
          to="/establecimientos"
        >
          Volver al listado
        </AppButton>
        {errorDetalle ? <Alert severity="warning">{errorDetalle}</Alert> : null}
      </Stack>
    );
  }

  return (
    <Stack spacing={2} sx={{ width: "100%", maxWidth: "100%" }}>
      <AppButton
        dsVariant="ghost"
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate("/establecimientos")}
        sx={{ color: "rgba(255,255,255,0.75)", alignSelf: "flex-start" }}
      >
        Volver
      </AppButton>

      <Paper elevation={0} sx={{ ...glassCard, p: 2.5 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "flex-start" }}>
          <Box
            sx={{
              width: 72,
              height: 72,
              borderRadius: "8px",
              border: `1px solid ${COLORS.border}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "rgba(1, 102, 255, 0.12)",
              flexShrink: 0,
            }}
          >
            <StorefrontIcon sx={{ fontSize: 40, color: COLORS.primary }} />
          </Box>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography
              sx={{
                fontFamily: '"Tactic Sans", sans-serif',
                fontWeight: 700,
                fontSize: { xs: "16px", sm: "20px" },
                color: COLORS.white,
                letterSpacing: "0.04em",
                lineHeight: 1.25,
              }}
            >
              {tituloPrincipal}
            </Typography>
            <Typography
              sx={{
                mt: 0.75,
                fontFamily: '"Tactic Sans", sans-serif',
                fontSize: "12px",
                fontWeight: 600,
                color: "rgba(255,255,255,0.75)",
                letterSpacing: "0.04em",
              }}
            >
              DNI/CUIT: {dash(detalle.documento)}
            </Typography>
            <Typography
              sx={{
                mt: 0.75,
                fontFamily: '"Tactic Sans", sans-serif',
                fontSize: "12px",
                fontWeight: 600,
                color: COLORS.primary,
                letterSpacing: "0.06em",
              }}
            >
              RUBRO: {dash(detalle.rubro_nombre)}
            </Typography>

            <Stack direction="row" spacing={1} alignItems="flex-start" sx={{ mt: 2 }}>
              <LocationOnIcon sx={{ color: COLORS.primary, fontSize: 22, mt: 0.25, flexShrink: 0 }} />
              <Box sx={{ minWidth: 0 }}>
                <Typography
                  sx={{
                    fontSize: "10px",
                    fontWeight: 700,
                    letterSpacing: "0.1em",
                    color: "rgba(255,255,255,0.45)",
                    mb: 0.5,
                  }}
                >
                  DOMICILIO
                </Typography>
                <Typography sx={{ fontSize: "15px", fontWeight: 600, color: COLORS.white, lineHeight: 1.35 }}>
                  {domicilioLinea}
                </Typography>
                {detalle.distrito_nombre?.trim() ? (
                  <Typography sx={{ fontSize: "12px", color: "rgba(255,255,255,0.6)", mt: 0.5 }}>
                    Distrito: {detalle.distrito_nombre.trim()}
                  </Typography>
                ) : null}
              </Box>
            </Stack>
          </Box>
        </Stack>
      </Paper>

      <Paper elevation={0} sx={{ ...glassCard, overflow: "hidden", p: 2 }}>
        <Stack spacing={1.5}>
          <Typography
            sx={{
              fontFamily: '"Tactic Sans", sans-serif',
              fontSize: "12px",
              fontWeight: 700,
              letterSpacing: "0.08em",
              color: COLORS.white,
            }}
          >
            Historial de actuaciones
          </Typography>
          {errorHistorial ? <Alert severity="error">{errorHistorial}</Alert> : null}
          {!errorHistorial ? (
            <DataTableMrtShell
              loading={loadingHistorial || historialTotal === null}
              loadingMode="overlay"
            >
              <MaterialReactTable table={tableHistorial} />
            </DataTableMrtShell>
          ) : null}
        </Stack>
      </Paper>
    </Stack>
  );
}
