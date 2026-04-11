import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import FilterAltIcon from "@mui/icons-material/FilterAlt";
import { Alert, Box, Grid, Stack, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_PaginationState,
} from "material-react-table";

import { AppButton, AppTextField } from "../../ui";
import { COLORS } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import {
  filtroContainerStyles,
  filtroTitleStyles,
} from "../Actuaciones/styles/filtroStyles";
import { DARK_TABLE_CONFIG } from "../Actuaciones/styles/actuacionesTableStyles";
import {
  getEstablecimientosOperativos,
  type IEstablecimientoOperativoListItem,
} from "../../api/establecimientosOperativosApi";
import { RubroChip } from "./components/RubroChip";

const DEFAULT_PAGE_SIZE = 20;

/**
 * Listado de fichas operativas (`establecimiento_operativo`) desde API.
 */
export default function EstablecimientosListPage() {
  const navigate = useNavigate();

  const [rows, setRows] = useState<IEstablecimientoOperativoListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [contrib, setContrib] = useState("");
  const [calle, setCalle] = useState("");
  const [distritoId, setDistritoId] = useState("");
  const [rubroId, setRubroId] = useState("");

  const [applied, setApplied] = useState({
    contrib: "",
    calle: "",
    distrito_id: "" as string,
    rubro_id: "" as string,
  });

  const [pagination, setPagination] = useState<MRT_PaginationState>({
    pageIndex: 0,
    pageSize: DEFAULT_PAGE_SIZE,
  });

  const parseOptionalInt = (s: string): number | undefined => {
    const t = s.trim();
    if (!t) return undefined;
    const n = Number.parseInt(t, 10);
    return Number.isFinite(n) ? n : undefined;
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getEstablecimientosOperativos({
        page: pagination.pageIndex + 1,
        page_size: pagination.pageSize,
        calle: applied.calle.trim() || undefined,
        contrib: applied.contrib.trim() || undefined,
        distrito_id: parseOptionalInt(applied.distrito_id),
        rubro_id: parseOptionalInt(applied.rubro_id),
      });
      setRows(res.items);
      setTotal(res.meta.total);
    } catch (e: unknown) {
      const msg =
        e && typeof e === "object" && "response" in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setError(msg ?? "No se pudo cargar el listado de establecimientos.");
      setRows([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [applied, pagination.pageIndex, pagination.pageSize]);

  useEffect(() => {
    void load();
  }, [load]);

  const onFiltrar = useCallback(() => {
    setApplied({
      contrib,
      calle,
      distrito_id: distritoId,
      rubro_id: rubroId,
    });
    setPagination((p) => ({ ...p, pageIndex: 0 }));
  }, [contrib, calle, distritoId, rubroId]);

  const columns = useMemo<MRT_ColumnDef<IEstablecimientoOperativoListItem>[]>(
    () => [
      { accessorKey: "calle", header: "CALLE", size: 200 },
      {
        accessorKey: "numero",
        header: "NÚMERO",
        size: 120,
        Cell: ({ cell }) => (cell.getValue() as string | null) ?? "—",
      },
      {
        accessorKey: "rubro_nombre",
        header: "RUBRO",
        size: 180,
        enableSorting: false,
        Cell: ({ row }) => (
          <RubroChip rubro={row.original.rubro_nombre?.trim() || "—"} />
        ),
      },
      {
        accessorKey: "contrib_nombre",
        header: "NOMBRE",
        size: 120,
        Cell: ({ cell }) => (cell.getValue() as string | null) ?? "—",
      },
      {
        accessorKey: "contrib_apellido",
        header: "APELLIDO",
        size: 120,
        Cell: ({ cell }) => (cell.getValue() as string | null) ?? "—",
      },
      {
        accessorKey: "documento",
        header: "DOCUMENTO",
        size: 120,
        Cell: ({ cell }) => (cell.getValue() as string | null) ?? "—",
      },
      {
        accessorKey: "distrito_nombre",
        header: "DISTRITO",
        size: 140,
        Cell: ({ cell }) => (cell.getValue() as string | null) ?? "—",
      },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data: rows,
    getRowId: (row) => String(row.id),
    enableEditing: false,
    enableRowSelection: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    manualPagination: true,
    rowCount: total,
    state: {
      pagination,
      isLoading: loading,
      showProgressBars: loading,
    },
    onPaginationChange: setPagination,
    muiTableBodyRowProps: () => ({
      sx: { cursor: "default" },
    }),
    displayColumnDefOptions: {
      "mrt-row-actions": { header: "ACCIONES", size: 140 },
    },
    enableRowActions: true,
    positionActionsColumn: "last",
    renderRowActions: ({ row }) => (
      <AppButton
        dsVariant="secondary"
        dsSize="sm"
        onClick={() => navigate(`/establecimientos/${row.original.id}`)}
        sx={{
          fontFamily: '"Tactic Sans", sans-serif',
          textTransform: "uppercase",
          fontSize: "10px",
          fontWeight: 600,
          letterSpacing: "0.06em",
          borderColor: COLORS.border,
          color: COLORS.white,
        }}
      >
        Ver ficha
      </AppButton>
    ),
  });

  const rangeLabel = useMemo(() => {
    if (total === 0) return "0 registros";
    const from = pagination.pageIndex * pagination.pageSize + 1;
    const to = Math.min((pagination.pageIndex + 1) * pagination.pageSize, total);
    return `${from}–${to} de ${total}`;
  }, [total, pagination.pageIndex, pagination.pageSize]);

  return (
    <Stack spacing={2} sx={{ width: "100%", maxWidth: "100%" }}>
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      <Box sx={filtroContainerStyles}>
        <Typography sx={filtroTitleStyles}>Filtros</Typography>
        <Grid container spacing={1.5} alignItems="flex-end">
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <AppTextField
              appearance="glass"
              fullWidth
              size="small"
              label="Contribuyente / razón social"
              placeholder="Coincide con API (contrib)"
              value={contrib}
              onChange={(e) => setContrib(e.target.value)}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <AppTextField
              appearance="glass"
              fullWidth
              size="small"
              label="Calle"
              value={calle}
              onChange={(e) => setCalle(e.target.value)}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <AppTextField
              appearance="glass"
              fullWidth
              size="small"
              label="ID distrito"
              placeholder="Opcional"
              value={distritoId}
              onChange={(e) => setDistritoId(e.target.value)}
              inputProps={{ inputMode: "numeric" }}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <AppTextField
              appearance="glass"
              fullWidth
              size="small"
              label="ID rubro"
              placeholder="Opcional"
              value={rubroId}
              onChange={(e) => setRubroId(e.target.value)}
              inputProps={{ inputMode: "numeric" }}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 2 }}>
            <AppButton
              dsVariant="primary"
              startIcon={<FilterAltIcon sx={{ fontSize: 18 }} />}
              onClick={onFiltrar}
              sx={{ fontFamily: '"Tactic Sans", sans-serif', fontWeight: 600 }}
            >
              Filtrar
            </AppButton>
          </Grid>
        </Grid>
      </Box>

      <Box sx={{ width: "100%", minWidth: 0, overflow: "hidden" }}>
        <MaterialReactTable table={table} />
        <Typography
          variant="caption"
          sx={{
            display: "block",
            mt: 1,
            fontFamily: '"Tactic Sans", sans-serif',
            color: "rgba(255,255,255,0.45)",
          }}
        >
          {rangeLabel} · datos de establecimientos operativos
        </Typography>
      </Box>
    </Stack>
  );
}
