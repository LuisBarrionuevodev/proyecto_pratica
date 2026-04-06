import { useMemo } from "react";
import { Box, Chip, Stack, TextField, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_RowSelectionState,
} from "material-react-table";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { DARK_TABLE_CONFIG } from "../../Actuaciones/styles/actuacionesTableStyles";
import { filtroItemStyles } from "../../Actuaciones/styles/filtroStyles";
import { AppButton, AppSelect } from "../../../ui";

const TIPO_INICIADOR_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "RELEVAMIENTO", label: "Relevamiento" },
  { value: "DENUNCIA", label: "Denuncia" },
  { value: "REINSPECCION_OFICIO", label: "Reinspección oficio" },
  { value: "REINSPECCION_NOTIFICACION", label: "Reinspección notificación" },
  { value: "VERIFICAR_INFORMAR_OFICIO", label: "Verificar e informar (oficio)" },
  { value: "RATIFICACION_CLAUSURA_OFICIO", label: "Ratificación clausura" },
  { value: "RATIFICACION_DECOMISO_OFICIO", label: "Ratificación decomiso" },
] as const;

const PRIORIDAD_OPTIONS = [
  { value: "", label: "Todas" },
  { value: "BAJA", label: "Baja" },
  { value: "MEDIA", label: "Media" },
  { value: "ALTA", label: "Alta" },
] as const;

const PRIORIDAD_CONFIG = {
  alta: { label: "Alta", color: "#ffd9a2", bg: "rgba(184,120,34,0.30)" },
  media: { label: "Media", color: "#c8dcff", bg: "rgba(58,103,182,0.30)" },
  baja: { label: "Baja", color: "#bdf2d7", bg: "rgba(28,115,80,0.30)" },
  none: { label: "Sin prioridad", color: "#c6d3ed", bg: "rgba(95,110,140,0.24)" },
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

const compactFiltroSx = {
  ...filtroItemStyles,
  minWidth: 0,
  flex: "1 1 120px",
  maxWidth: 220,
} as const;

/** Filtros locales sobre el pool del día (Asignación); sin catálogo remoto de calles. */
export type AsignacionPoolFilters = {
  tipo: string;
  prioridad_categoria: "" | "BAJA" | "MEDIA" | "ALTA";
  distrito: string;
  /** Búsqueda de texto sobre domicilio, rubro, tipo, etc. */
  q: string;
};

type TableProps = {
  rows: IRutaIniciadorPendienteRow[];
  totalEnPool: number;
  selectedIds: number[];
  assignedIniciadorIds: Set<number>;
  filters: AsignacionPoolFilters;
  onChangeFilters: (next: AsignacionPoolFilters) => void;
  onSelectionChange: (ids: number[]) => void;
  onAssignSelected: () => void;
  distritoOptions: { value: string; label: string }[];
  onSincronizarDetalle?: () => void;
  detailLoading?: boolean;
};

function IniciadoresPoolTableMrt({
  rows,
  totalEnPool,
  selectedIds,
  assignedIniciadorIds,
  onSelectionChange,
  onAssignSelected,
}: Omit<TableProps, "filters" | "onChangeFilters" | "distritoOptions" | "onSincronizarDetalle" | "detailLoading">) {
  const rowSelection = useMemo<MRT_RowSelectionState>(
    () => Object.fromEntries(selectedIds.map((id) => [String(id), true])),
    [selectedIds]
  );

  const columns = useMemo<MRT_ColumnDef<IRutaIniciadorPendienteRow>[]>(
    () => [
      {
        id: "estado",
        header: "Estado",
        size: 110,
        Cell: ({ row }) => {
          const asignado = assignedIniciadorIds.has(row.original.id);
          return (
            <Chip
              label={asignado ? "En ruta" : "Sin asignar"}
              size="small"
              color={asignado ? "success" : "default"}
              variant="outlined"
              sx={{ fontFamily: '"Tactic Sans", sans-serif', fontSize: "11px" }}
            />
          );
        },
      },
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
    [assignedIniciadorIds]
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data: rows,
    getRowId: (row) => String(row.id),

    enableEditing: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,

    enableRowSelection: (row) => !assignedIniciadorIds.has(row.original.id),
    enableSelectAll: false,

    state: { rowSelection },
    onRowSelectionChange: (updaterOrValue) => {
      const next =
        typeof updaterOrValue === "function" ? updaterOrValue(rowSelection) : updaterOrValue;
      onSelectionChange(
        Object.keys(next)
          .filter((k) => next[k])
          .map(Number)
      );
    },

    manualPagination: false,

    renderTopToolbarCustomActions: () => (
      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ pl: 0.5 }} flexWrap="wrap" useFlexGap>
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.7)" }}>
          Ítems en pool: {totalEnPool} · Filas visibles: {rows.length}
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

  return <MaterialReactTable table={table} />;
}

const FILTROS_VACIOS: AsignacionPoolFilters = {
  tipo: "",
  prioridad_categoria: "",
  distrito: "",
  q: "",
};

export type TablaIniciadoresPendientesProps = TableProps;

/**
 * Tabla de iniciadores del pool del día (Asignación): filtros locales, sin catálogo de calles ni carga global.
 */
function TablaIniciadoresPendientes({
  rows,
  totalEnPool,
  selectedIds,
  assignedIniciadorIds,
  filters,
  onChangeFilters,
  onSelectionChange,
  onAssignSelected,
  distritoOptions,
  onSincronizarDetalle,
  detailLoading,
}: TableProps) {
  /** Solo si el pool mezcla más de un distrito: el filtro aporta valor; si no, no mostramos el control. */
  const mostrarFiltroDistrito = distritoOptions.length > 2;

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.35 }}>
        Distribuí entre grupos lo elegido en Planificación. Los filtros aplican solo sobre este listado (sin consultas
        globales). La búsqueda es local sobre domicilio, rubro y datos visibles.
      </Typography>
      <Stack
        direction="row"
        spacing={0.75}
        flexWrap="wrap"
        alignItems="flex-end"
        justifyContent="space-between"
        useFlexGap
        gap={1}
      >
        <Stack direction="row" spacing={0.75} flexWrap="wrap" alignItems="flex-end" useFlexGap sx={{ flex: 1 }}>
          <Box sx={{ ...compactFiltroSx, flex: "1 1 140px", minWidth: 132 }}>
            <AppSelect
              appearance="dense"
              label="Tipo"
              value={filters.tipo}
              onChange={(e) => onChangeFilters({ ...filters, tipo: String(e.target.value) })}
              fullWidth
              options={[...TIPO_INICIADOR_OPTIONS]}
            />
          </Box>
          <Box sx={{ ...compactFiltroSx, flex: "0 1 118px", minWidth: 108 }}>
            <AppSelect
              appearance="dense"
              label="Prioridad"
              value={filters.prioridad_categoria}
              onChange={(e) =>
                onChangeFilters({
                  ...filters,
                  prioridad_categoria: String(e.target.value) as AsignacionPoolFilters["prioridad_categoria"],
                })
              }
              fullWidth
              options={[...PRIORIDAD_OPTIONS]}
            />
          </Box>
          {mostrarFiltroDistrito ? (
            <Box sx={{ ...compactFiltroSx, flex: "1 1 140px", minWidth: 128 }}>
              <AppSelect
                appearance="dense"
                label="Distrito (en el pool)"
                value={filters.distrito}
                onChange={(e) => onChangeFilters({ ...filters, distrito: String(e.target.value) })}
                fullWidth
                options={distritoOptions}
              />
            </Box>
          ) : null}
          <Box sx={{ ...compactFiltroSx, flex: "2 1 200px", minWidth: 160, maxWidth: 320 }}>
            <TextField
              size="small"
              fullWidth
              label="Buscar en este listado"
              placeholder="Texto en domicilio, rubro…"
              value={filters.q}
              onChange={(e) => onChangeFilters({ ...filters, q: e.target.value })}
              sx={{
                "& .MuiInputBase-root": {
                  fontFamily: '"Tactic Sans", sans-serif',
                  fontSize: "0.875rem",
                },
              }}
            />
          </Box>
        </Stack>
        {onSincronizarDetalle ? (
          <AppButton
            dsVariant="secondary"
            dsSize="sm"
            disabled={detailLoading}
            onClick={() => onSincronizarDetalle()}
          >
            {detailLoading ? "Sincronizando…" : "Sincronizar borrador"}
          </AppButton>
        ) : null}
      </Stack>

      <IniciadoresPoolTableMrt
        rows={rows}
        totalEnPool={totalEnPool}
        selectedIds={selectedIds}
        assignedIniciadorIds={assignedIniciadorIds}
        onSelectionChange={onSelectionChange}
        onAssignSelected={onAssignSelected}
      />
    </Box>
  );
}

export default TablaIniciadoresPendientes;
export { FILTROS_VACIOS as ASIGNACION_POOL_FILTROS_VACIOS };
