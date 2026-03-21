import { useMemo } from "react";
import { Box, Chip, Stack, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_PaginationState,
  type MRT_RowSelectionState,
} from "material-react-table";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { DARK_TABLE_CONFIG } from "../../Actuaciones/styles/actuacionesTableStyles";
import { filtroItemStyles } from "../../Actuaciones/styles/filtroStyles";
import { AppButton, AppSelect, AppTextField } from "../../../ui";

// ─── Helpers de presentación ────────────────────────────────────────────────

const PRIORIDAD_CONFIG = {
  alta:  { label: "Alta",         color: "#ffd9a2", bg: "rgba(184,120,34,0.30)" },
  media: { label: "Media",        color: "#c8dcff", bg: "rgba(58,103,182,0.30)" },
  baja:  { label: "Baja",         color: "#bdf2d7", bg: "rgba(28,115,80,0.30)"  },
  none:  { label: "Sin prioridad",color: "#c6d3ed", bg: "rgba(95,110,140,0.24)" },
} as const;

function prioridadCfg(p: number | null | undefined) {
  if (p === null || p === undefined) return PRIORIDAD_CONFIG.none;
  if (p >= 3) return PRIORIDAD_CONFIG.alta;
  if (p === 2) return PRIORIDAD_CONFIG.media;
  return PRIORIDAD_CONFIG.baja;
}

const TIPO_SX = {
  fontSize: "11px",
  height: 22,
  backgroundColor: "rgba(23, 62, 140, 0.28)",
  color: "#c9ddff",
  fontFamily: '"Tactic Sans", sans-serif',
} as const;

// ─── Props ───────────────────────────────────────────────────────────────────

interface Props {
  rows: IRutaIniciadorPendienteRow[];
  total: number;
  page: number;
  perPage: number;
  loading: boolean;
  selectedIds: number[];
  filters: {
    q: string;
    tipo: string;
    prioridad: string;
    distrito: string;
    turno_sugerido: string;
  };
  onChangeFilters: (next: Props["filters"]) => void;
  onPageChange: (nextPage: number) => void;
  onPerPageChange: (nextPerPage: number) => void;
  onSelectionChange: (ids: number[]) => void;
  onAssignSelected: () => void;
}

// ─── Componente ──────────────────────────────────────────────────────────────

/**
 * Tabla de iniciadores pendientes de asignación a ruta.
 * Usa MRT con configuración dark institucional, paginación server-side
 * y selección de filas sincronizada con el contenedor padre.
 */
const TablaIniciadoresPendientes = ({
  rows,
  total,
  page,
  perPage,
  loading,
  selectedIds,
  filters,
  onChangeFilters,
  onPageChange,
  onPerPageChange,
  onSelectionChange,
  onAssignSelected,
}: Props) => {
  // ── Sincronización selección ──────────────────────────────────────────────
  const rowSelection = useMemo<MRT_RowSelectionState>(
    () => Object.fromEntries(selectedIds.map((id) => [String(id), true])),
    [selectedIds]
  );

  // ── Paginación (MRT usa 0-based, API usa 1-based) ─────────────────────────
  const pagination = useMemo<MRT_PaginationState>(
    () => ({ pageIndex: page - 1, pageSize: perPage }),
    [page, perPage]
  );

  // ── Columnas ──────────────────────────────────────────────────────────────
  const columns = useMemo<MRT_ColumnDef<IRutaIniciadorPendienteRow>[]>(
    () => [
      {
        id: "tipo",
        accessorKey: "tipo_iniciador",
        header: "Tipo",
        size: 160,
        Cell: ({ row }) => {
          const label = row.original.badges?.tipo_label ?? row.original.tipo_iniciador;
          return <Chip label={label} size="small" sx={TIPO_SX} />;
        },
      },
      {
        id: "fecha",
        accessorKey: "fecha_origen",
        header: "Fecha",
        size: 110,
        Cell: ({ row }) => <>{row.original.fecha_origen?.slice(0, 10) ?? "-"}</>,
      },
      {
        id: "prioridad",
        accessorKey: "prioridad",
        header: "Prioridad",
        size: 120,
        Cell: ({ row }) => {
          const cfg = prioridadCfg(row.original.prioridad);
          return (
            <Chip
              label={cfg.label}
              size="small"
              sx={{
                fontSize: "11px",
                height: 22,
                backgroundColor: cfg.bg,
                color: cfg.color,
                fontFamily: '"Tactic Sans", sans-serif',
              }}
            />
          );
        },
      },
      {
        id: "domicilio",
        header: "Domicilio",
        size: 260,
        Cell: ({ row }) => {
          const d =
            row.original.domicilio_texto ??
            `${row.original.domicilio?.calle ?? "-"} ${row.original.domicilio?.numero ?? ""}`.trim();
          return <>{d || "-"}</>;
        },
      },
      {
        id: "distrito",
        header: "Distrito",
        size: 130,
        Cell: ({ row }) => (
          <>{row.original.distrito_nombre ?? row.original.domicilio?.distrito_nombre ?? "-"}</>
        ),
      },
      {
        id: "rubro",
        header: "Rubro",
        size: 150,
        Cell: ({ row }) => (
          <>{row.original.rubro_nombre ?? row.original.domicilio?.rubro ?? "-"}</>
        ),
      },
      {
        id: "observaciones",
        accessorKey: "observaciones",
        header: "Observaciones",
        size: 200,
        Cell: ({ row }) => {
          const obs = row.original.observaciones ?? "-";
          return <>{obs.length > 60 ? `${obs.slice(0, 57).trimEnd()}…` : obs}</>;
        },
      },
    ],
    []
  );

  // ── Tabla ─────────────────────────────────────────────────────────────────
  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data: rows,
    getRowId: (row) => String(row.id),

    // Desactivar edición y filtros de columna (gestión externa)
    enableEditing: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,

    // Selección de filas
    enableRowSelection: true,
    state: { rowSelection, pagination, isLoading: loading },
    onRowSelectionChange: (updaterOrValue) => {
      const next =
        typeof updaterOrValue === "function" ? updaterOrValue(rowSelection) : updaterOrValue;
      onSelectionChange(
        Object.keys(next)
          .filter((k) => next[k])
          .map(Number)
      );
    },

    // Paginación server-side
    manualPagination: true,
    rowCount: total,
    onPaginationChange: (updaterOrValue) => {
      const next =
        typeof updaterOrValue === "function" ? updaterOrValue(pagination) : updaterOrValue;
      if (next.pageIndex !== pagination.pageIndex) onPageChange(next.pageIndex + 1);
      if (next.pageSize !== pagination.pageSize) onPerPageChange(next.pageSize);
    },

    // Toolbar superior: total + botón acción
    renderTopToolbarCustomActions: () => (
      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ pl: 0.5 }}>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.7)" }}>
          Total pendientes: {total}
        </Typography>
        <Chip
          label={`${selectedIds.length} seleccionados`}
          color="primary"
          variant="outlined"
          size="small"
        />
        <AppButton
          dsVariant="primary"
          dsSize="sm"
          onClick={onAssignSelected}
          disabled={selectedIds.length === 0}
        >
          Asignar seleccionados
        </AppButton>
      </Stack>
    ),
  });

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
      {/* Barra de filtros externos */}
      <Stack direction="row" spacing={1} flexWrap="wrap" alignItems="flex-end">
        <Box sx={{ ...filtroItemStyles, minWidth: 200 }}>
          <AppTextField
            appearance="dense"
            label="Buscar"
            value={filters.q}
            onChange={(e) => onChangeFilters({ ...filters, q: e.target.value })}
            fullWidth
          />
        </Box>
        <Box sx={{ ...filtroItemStyles, minWidth: 170 }}>
          <AppSelect
            appearance="dense"
            label="Tipo"
            value={filters.tipo}
            onChange={(e) => onChangeFilters({ ...filters, tipo: String(e.target.value) })}
            fullWidth
            options={[
              { value: "", label: "Todos" },
              { value: "RELEVAMIENTO", label: "Relevamiento" },
              { value: "DENUNCIA", label: "Denuncia" },
              { value: "REINSPECCION_OFICIO", label: "Reinspeccion oficio" },
              { value: "REINSPECCION_NOTIFICACION", label: "Reinspeccion notificacion" },
            ]}
          />
        </Box>
        <Box sx={{ ...filtroItemStyles, width: 120 }}>
          <AppTextField
            appearance="dense"
            label="Prioridad"
            value={filters.prioridad}
            onChange={(e) => onChangeFilters({ ...filters, prioridad: e.target.value })}
            fullWidth
          />
        </Box>
        <Box sx={{ ...filtroItemStyles, width: 120 }}>
          <AppTextField
            appearance="dense"
            label="Distrito"
            value={filters.distrito}
            onChange={(e) => onChangeFilters({ ...filters, distrito: e.target.value })}
            fullWidth
          />
        </Box>
        <Box sx={{ ...filtroItemStyles, minWidth: 150 }}>
          <AppSelect
            appearance="dense"
            label="Turno sugerido"
            value={filters.turno_sugerido}
            onChange={(e) =>
              onChangeFilters({ ...filters, turno_sugerido: String(e.target.value) })
            }
            fullWidth
            options={[
              { value: "", label: "Todos" },
              { value: "MANIANA", label: "Mañana" },
              { value: "TARDE", label: "Tarde" },
            ]}
          />
        </Box>
      </Stack>

      <MaterialReactTable table={table} />
    </Box>
  );
};

export default TablaIniciadoresPendientes;
