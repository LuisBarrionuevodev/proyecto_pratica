import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import SearchIcon from "@mui/icons-material/Search";
import { Alert, Box, Stack, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_PaginationState,
  type MRT_Updater,
} from "material-react-table";

import { AppButton, AppTextField } from "../../ui";
import { COLORS } from "../CargarActuaciones/styles/cargarActuacionesStyles";
import {
  filtroButtonPrimaryStyles,
  filtroButtonsStyles,
  filtroContainerStyles,
  filtroGridStyles,
  filtroItemStyles,
  filtroTitleStyles,
} from "../Actuaciones/styles/filtroStyles";
import { DARK_TABLE_CONFIG, exportButtonStyles } from "../Actuaciones/styles/actuacionesTableStyles";
import {
  BandejaEllipsisCell,
  BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
} from "../Actuaciones/Components/bandejaTableCells";
import {
  getEstablecimientosOperativos,
  type IEstablecimientoOperativoListItem,
} from "../../api/establecimientosOperativosApi";
import { RubroChip } from "./components/RubroChip";
import { DataTableMrtShell } from "../../components/dataTable/DataTableMrtShell";
import { FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING } from "../../styles/functionalPageShell";

const DEFAULT_PAGE_SIZE = 20;

function parseOptionalInt(s: string): number | undefined {
  const t = s.trim();
  if (!t) return undefined;
  const n = Number.parseInt(t, 10);
  return Number.isFinite(n) ? n : undefined;
}

type EstablecimientosListResultsProps = {
  rows: IEstablecimientoOperativoListItem[];
  total: number;
  loading: boolean;
  pagination: MRT_PaginationState;
  onPaginationChange: (updater: MRT_Updater<MRT_PaginationState>) => void;
};

/**
 * Tabla de resultados: se monta solo cuando el usuario ya aplicó un filtro (evita hook condicional en el padre).
 */
function EstablecimientosListResults({
  rows,
  total,
  loading,
  pagination,
  onPaginationChange,
}: EstablecimientosListResultsProps) {
  const navigate = useNavigate();

  const columns = useMemo<MRT_ColumnDef<IEstablecimientoOperativoListItem>[]>(
    () => [
      {
        accessorKey: "calle",
        header: "CALLE",
        size: 200,
        Cell: ({ cell }) => <BandejaEllipsisCell value={(cell.getValue() as string | null) ?? "—"} />,
      },
      {
        accessorKey: "numero",
        header: "NÚMERO",
        size: 120,
        Cell: ({ cell }) => <BandejaEllipsisCell value={(cell.getValue() as string | null) ?? "—"} />,
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
        Cell: ({ cell }) => <BandejaEllipsisCell value={(cell.getValue() as string | null) ?? "—"} />,
      },
      {
        accessorKey: "contrib_apellido",
        header: "APELLIDO",
        size: 120,
        Cell: ({ cell }) => <BandejaEllipsisCell value={(cell.getValue() as string | null) ?? "—"} />,
      },
      {
        accessorKey: "documento",
        header: "DOCUMENTO",
        size: 120,
        Cell: ({ cell }) => <BandejaEllipsisCell value={(cell.getValue() as string | null) ?? "—"} />,
      },
      {
        accessorKey: "distrito_nombre",
        header: "DISTRITO",
        size: 140,
        Cell: ({ cell }) => <BandejaEllipsisCell value={(cell.getValue() as string | null) ?? "—"} />,
      },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
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
    onPaginationChange,
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
        sx={exportButtonStyles}
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
    <DataTableMrtShell loading={loading} loadingMode="progress"
      footer={
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
      }
    >
      <MaterialReactTable table={table} />
    </DataTableMrtShell>
  );
}

/**
 * Listado de fichas operativas (`establecimiento_operativo`) desde API.
 * La tabla se muestra solo después de aplicar filtros (misma familia visual que Pendientes / Oficio).
 */
export default function EstablecimientosListPage() {
  const [filtroAplicado, setFiltroAplicado] = useState(false);

  const [rows, setRows] = useState<IEstablecimientoOperativoListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
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

  const load = useCallback(async () => {
    if (!filtroAplicado) return;
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
  }, [filtroAplicado, applied, pagination.pageIndex, pagination.pageSize]);

  useEffect(() => {
    void load();
  }, [load]);

  const onFiltrar = useCallback(() => {
    setFiltroAplicado(true);
    setApplied({
      contrib,
      calle,
      distrito_id: distritoId,
      rubro_id: rubroId,
    });
    setPagination((p) => ({ ...p, pageIndex: 0 }));
  }, [contrib, calle, distritoId, rubroId]);

  return (
    <Stack spacing={FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING} sx={{ width: "100%", maxWidth: "100%" }}>
      {error ? (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}

      <Box sx={filtroContainerStyles}>
        <Typography sx={filtroTitleStyles}>Filtros</Typography>
        <Box sx={filtroGridStyles}>
          <Box sx={filtroItemStyles}>
            <AppTextField
              appearance="dense"
              fullWidth
              label="Contribuyente / razón social"
              placeholder="Coincide con API (contrib)"
              value={contrib}
              onChange={(e) => setContrib(e.target.value)}
              variant="outlined"
            />
          </Box>
          <Box sx={filtroItemStyles}>
            <AppTextField
              appearance="dense"
              fullWidth
              label="Calle"
              value={calle}
              onChange={(e) => setCalle(e.target.value)}
              variant="outlined"
            />
          </Box>
          <Box sx={filtroItemStyles}>
            <AppTextField
              appearance="dense"
              fullWidth
              label="ID distrito"
              placeholder="Opcional"
              value={distritoId}
              onChange={(e) => setDistritoId(e.target.value)}
              variant="outlined"
              inputProps={{ inputMode: "numeric" }}
            />
          </Box>
          <Box sx={filtroItemStyles}>
            <AppTextField
              appearance="dense"
              fullWidth
              label="ID rubro"
              placeholder="Opcional"
              value={rubroId}
              onChange={(e) => setRubroId(e.target.value)}
              variant="outlined"
              inputProps={{ inputMode: "numeric" }}
            />
          </Box>
        </Box>
        <Box sx={filtroButtonsStyles}>
          <AppButton
            dsVariant="primary"
            dsSize="sm"
            startIcon={<SearchIcon sx={{ fontSize: 18 }} />}
            onClick={onFiltrar}
            sx={filtroButtonPrimaryStyles}
          >
            Filtrar
          </AppButton>
        </Box>
      </Box>

      {!filtroAplicado ? (
        <Typography
          sx={{
            fontFamily: '"Tactic Sans", sans-serif',
            fontSize: "14px",
            color: "rgba(255,255,255,0.5)",
            py: 2,
          }}
        >
          Completá criterios de búsqueda y tocá <strong>Filtrar</strong> para ver el listado.
        </Typography>
      ) : (
        <EstablecimientosListResults
          rows={rows}
          total={total}
          loading={loading}
          pagination={pagination}
          onPaginationChange={setPagination}
        />
      )}
    </Stack>
  );
}
