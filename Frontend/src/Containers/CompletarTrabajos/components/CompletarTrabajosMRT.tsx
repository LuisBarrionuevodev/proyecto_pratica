import { useMemo } from "react";
import { Box, Chip, CircularProgress, IconButton, Tooltip, Typography } from "@mui/material";
import AssignmentTurnedInIcon from "@mui/icons-material/AssignmentTurnedIn";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";
import {
  DATA_TABLE_MRT_GLASS_COLORS,
  dataTableShellSx,
  MRT_DATA_TABLE_GLASS_PRESET,
} from "../../../styles/mrtGlassDataTablePreset";

function dashIfEmpty(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function estadoChipColor(v: string | null | undefined): "default" | "success" | "warning" | "info" {
  const u = (v ?? "").toUpperCase();
  if (u.includes("FINAL")) return "success";
  if (u.includes("PROCESO") || u.includes("EN_")) return "info";
  if (u.includes("PEND")) return "warning";
  return "default";
}

export type CompletarTrabajosMRTProps = {
  rows: ICompletarTrabajoPendienteRow[];
  loading: boolean;
  total: number;
  page: number;
  perPage: number;
  onPageChange: (nextPage: number) => void;
  onPerPageChange: (nextPerPage: number) => void;
  /** Abre el modal de completar con la fila seleccionada. */
  onOpenCompletarModal: (row: ICompletarTrabajoPendienteRow) => void;
};

/**
 * Listado resumen (solo lectura). El cierre se hace en `CompletarTrabajoModal`.
 */
export function CompletarTrabajosMRT({
  rows,
  loading,
  total,
  page,
  perPage,
  onPageChange,
  onPerPageChange,
  onOpenCompletarModal,
}: CompletarTrabajosMRTProps) {
  const pagination = useMemo(() => ({ pageIndex: page - 1, pageSize: perPage }), [page, perPage]);

  const columns = useMemo<MRT_ColumnDef<ICompletarTrabajoPendienteRow>[]>(
    () => [
      {
        accessorKey: "fecha_actuacion",
        header: "Fecha",
        size: 100,
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "tipo_iniciador",
        header: "Iniciador",
        size: 130,
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "orden_trabajo_numero",
        header: "OT",
        size: 88,
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "tipo_actuacion",
        header: "Tipo actuación",
        size: 150,
        Cell: ({ row }) => (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.25 }}>
            <Typography variant="body2" sx={{ color: DATA_TABLE_MRT_GLASS_COLORS.white, fontSize: "11px" }}>
              {dashIfEmpty(row.original.tipo_actuacion)}
            </Typography>
            {row.original.tipo_actuacion_esperado ? (
              <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.45)", fontSize: "10px" }}>
                Ref.: {row.original.tipo_actuacion_esperado}
              </Typography>
            ) : null}
          </Box>
        ),
      },
      {
        id: "domicilio_resumen",
        header: "Domicilio",
        size: 200,
        Cell: ({ row }) => (
          <span>
            {dashIfEmpty(
              row.original.domicilio_texto?.trim() ||
                formatActuacionListDomicilioLinea(row.original).trim() ||
                null
            )}
          </span>
        ),
      },
      {
        accessorKey: "rubro_nombre",
        header: "Rubro",
        size: 120,
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "contraproducencia",
        header: "Contraproducción",
        size: 140,
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "inspectores_texto",
        header: "Inspectores",
        size: 150,
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "grupo_nombre",
        header: "Grupo",
        size: 100,
        Cell: ({ cell }) => <span>{dashIfEmpty(cell.getValue())}</span>,
      },
      {
        accessorKey: "estado_operativo",
        header: "Estado",
        size: 110,
        Cell: ({ cell }) => (
          <Chip
            size="small"
            label={dashIfEmpty(cell.getValue())}
            color={estadoChipColor(cell.getValue() as string)}
            variant="outlined"
            sx={{
              borderColor: "rgba(255,255,255,0.25)",
              color: DATA_TABLE_MRT_GLASS_COLORS.white,
              fontSize: "10px",
            }}
          />
        ),
      },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...MRT_DATA_TABLE_GLASS_PRESET,
    enableEditing: false,
    enableRowSelection: false,
    enableSelectAll: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enablePagination: true,
    enableSorting: true,
    muiTableContainerProps: {
      sx: {
        ...((MRT_DATA_TABLE_GLASS_PRESET.muiTableContainerProps as { sx?: object })?.sx ?? {}),
        maxHeight: "calc(100vh - 280px)",
      },
    },
    columns,
    data: rows,
    getRowId: (r) => String(r.ruta_item_id),
    enableRowActions: true,
    positionActionsColumn: "first",
    manualPagination: true,
    rowCount: total,
    state: {
      pagination,
      isLoading: loading,
    },
    onPaginationChange: (updaterOrValue) => {
      const next =
        typeof updaterOrValue === "function" ? updaterOrValue(pagination) : updaterOrValue;
      if (next.pageIndex !== pagination.pageIndex) onPageChange(next.pageIndex + 1);
      if (next.pageSize !== pagination.pageSize) onPerPageChange(next.pageSize);
    },
    initialState: {
      density: "compact",
    },
    renderRowActions: ({ row }) => (
      <Tooltip title="Completar trabajo">
        <IconButton
          size="small"
          disabled={loading}
          sx={{
            color: DATA_TABLE_MRT_GLASS_COLORS.white,
            "&:hover": {
              color: DATA_TABLE_MRT_GLASS_COLORS.primary,
              backgroundColor: "rgba(1, 102, 255, 0.15)",
            },
            "&.Mui-disabled": { color: "#555" },
          }}
          onClick={() => onOpenCompletarModal(row.original)}
          aria-label="Completar trabajo"
        >
          <AssignmentTurnedInIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    ),
  });

  return (
    <Box sx={{ position: "relative", display: "flex", flexDirection: "column", gap: 1 }}>
      <Box sx={{ position: "relative" }}>
        {loading && (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              zIndex: 2,
              bgcolor: "rgba(0, 0, 0, 0.45)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
              gap: 1,
              borderRadius: "8px",
            }}
          >
            <CircularProgress size={28} sx={{ color: DATA_TABLE_MRT_GLASS_COLORS.primary }} />
            <Typography
              variant="body2"
              sx={{ fontFamily: '"Tactic Sans", sans-serif', color: "rgba(255,255,255,0.75)" }}
            >
              Cargando trabajos…
            </Typography>
          </Box>
        )}
        <Box sx={dataTableShellSx}>
          <MaterialReactTable table={table} />
        </Box>
      </Box>
      <Typography
        variant="caption"
        sx={{
          fontFamily: '"Tactic Sans", sans-serif',
          color: "rgba(255,255,255,0.55)",
          display: "block",
        }}
      >
        Tocá el ícono de completar para abrir el formulario. Sin contraproducencia = visita realizada.
      </Typography>
    </Box>
  );
}
