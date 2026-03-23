import { useCallback, useEffect, useMemo, useState } from "react";
import { Autocomplete, Box, Chip, Stack, TextField, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_PaginationState,
  type MRT_Row,
  type MRT_RowSelectionState,
} from "material-react-table";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import {
  fetchCallesCatalogo,
  fetchDistritosCatalogo,
  type CalleCatalogoItem,
  type DistritoCatalogoItem,
} from "../../../api/geolocalizacionApi";
import { DARK_TABLE_CONFIG } from "../../Actuaciones/styles/actuacionesTableStyles";
import { filtroItemStyles } from "../../Actuaciones/styles/filtroStyles";
import { AppButton, AppSelect } from "../../../ui";

// ─── Valores alineados al backend (`TipoIniciadorLiteral`) ───

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

/** Mapeo UI: Baja=1, Media=2, Alta>=3 (backend `prioridad_categoria`). */
const PRIORIDAD_OPTIONS = [
  { value: "", label: "Todas" },
  { value: "BAJA", label: "Baja" },
  { value: "MEDIA", label: "Media" },
  { value: "ALTA", label: "Alta" },
] as const;

// ─── Helpers de presentación ────────────────────────────────────────────────

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

function iniciadorGlobalFilterFn(
  row: MRT_Row<IRutaIniciadorPendienteRow>,
  _columnId: string,
  filterValue: unknown
): boolean {
  const search = String(filterValue ?? "")
    .toLowerCase()
    .trim();
  if (!search) return true;
  const r = row.original;
  const dom =
    r.domicilio_texto ?? `${r.domicilio?.calle ?? "-"} ${r.domicilio?.numero ?? ""}`.trim();
  const parts = [
    r.tipo_iniciador,
    r.badges?.tipo_label,
    String(r.prioridad ?? ""),
    dom,
    r.distrito_nombre,
    r.domicilio?.distrito_nombre,
    r.rubro_nombre,
    r.domicilio?.rubro,
    r.observaciones,
    r.fecha_origen,
    String(r.id),
  ];
  const hay = parts.filter(Boolean).join(" ").toLowerCase();
  return hay.includes(search);
}

export type IniciadoresPendientesFilters = {
  tipo: string;
  prioridad_categoria: "" | "BAJA" | "MEDIA" | "ALTA";
  distrito: string;
  calle_catalogo_id: number | null;
  turno_sugerido: string;
};

type MrtBlockProps = {
  rows: IRutaIniciadorPendienteRow[];
  total: number;
  page: number;
  perPage: number;
  loading: boolean;
  selectedIds: number[];
  onPageChange: (nextPage: number) => void;
  onPerPageChange: (nextPerPage: number) => void;
  onSelectionChange: (ids: number[]) => void;
  onAssignSelected: () => void;
};

/**
 * Tabla MRT montada solo cuando ya hubo interacción con filtros (evita hooks condicionales en el padre).
 */
function IniciadoresPendientesTableMrt({
  rows,
  total,
  page,
  perPage,
  loading,
  selectedIds,
  onPageChange,
  onPerPageChange,
  onSelectionChange,
  onAssignSelected,
}: MrtBlockProps) {
  const rowSelection = useMemo<MRT_RowSelectionState>(
    () => Object.fromEntries(selectedIds.map((id) => [String(id), true])),
    [selectedIds]
  );

  const pagination = useMemo<MRT_PaginationState>(
    () => ({ pageIndex: page - 1, pageSize: perPage }),
    [page, perPage]
  );

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

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    columns,
    data: rows,
    getRowId: (row) => String(row.id),

    enableEditing: false,
    enableColumnFilters: false,
    enableGlobalFilter: true,
    globalFilterFn: iniciadorGlobalFilterFn,
    enableSelectAll: false,

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

    manualPagination: true,
    rowCount: total,
    onPaginationChange: (updaterOrValue) => {
      const next =
        typeof updaterOrValue === "function" ? updaterOrValue(pagination) : updaterOrValue;
      if (next.pageIndex !== pagination.pageIndex) onPageChange(next.pageIndex + 1);
      if (next.pageSize !== pagination.pageSize) onPerPageChange(next.pageSize);
    },

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

  return <MaterialReactTable table={table} />;
}

// ─── Props panel completo ───────────────────────────────────────────────────

interface Props {
  tablaVisible: boolean;
  rows: IRutaIniciadorPendienteRow[];
  total: number;
  page: number;
  perPage: number;
  loading: boolean;
  selectedIds: number[];
  filters: IniciadoresPendientesFilters;
  onChangeFilters: (next: IniciadoresPendientesFilters) => void;
  onRefrescar: () => void;
  onPageChange: (nextPage: number) => void;
  onPerPageChange: (nextPerPage: number) => void;
  onSelectionChange: (ids: number[]) => void;
  onAssignSelected: () => void;
}

/**
 * Filtros por catálogo: al cambiar cualquiera se consulta el servidor y se muestra la tabla.
 * Refrescar limpia filtros y oculta la tabla. Búsqueda MRT solo sobre la página cargada.
 */
const TablaIniciadoresPendientes = ({
  tablaVisible,
  rows,
  total,
  page,
  perPage,
  loading,
  selectedIds,
  filters,
  onChangeFilters,
  onRefrescar,
  onPageChange,
  onPerPageChange,
  onSelectionChange,
  onAssignSelected,
}: Props) => {
  const [distritos, setDistritos] = useState<DistritoCatalogoItem[]>([]);
  const [calleOptions, setCalleOptions] = useState<CalleCatalogoItem[]>([]);
  const [calleInput, setCalleInput] = useState("");
  const [calleValue, setCalleValue] = useState<CalleCatalogoItem | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchDistritosCatalogo()
      .then((res) => {
        if (!cancelled) setDistritos(res.items ?? []);
      })
      .catch(() => {
        if (!cancelled) setDistritos([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (filters.calle_catalogo_id == null) {
      setCalleValue(null);
      setCalleInput("");
      return;
    }
    if (calleValue?.id === filters.calle_catalogo_id) return;
    let cancelled = false;
    void fetchCallesCatalogo("", 200).then((res) => {
      if (cancelled) return;
      const found = res.items.find((c) => c.id === filters.calle_catalogo_id);
      if (found) {
        setCalleValue(found);
        setCalleInput(found.nombre);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [filters.calle_catalogo_id, calleValue?.id]);

  useEffect(() => {
    const t = window.setTimeout(() => {
      void fetchCallesCatalogo(calleInput, 25)
        .then((res) => setCalleOptions(res.items ?? []))
        .catch(() => setCalleOptions([]));
    }, 280);
    return () => window.clearTimeout(t);
  }, [calleInput]);

  const distritoOptions = useMemo(
    () => [
      { value: "", label: "Todos" },
      ...distritos.map((d) => ({ value: String(d.id), label: d.nombre || `Distrito #${d.id}` })),
    ],
    [distritos]
  );

  const mergeCalleOptions = useCallback((selected: CalleCatalogoItem | null, opts: CalleCatalogoItem[]) => {
    if (!selected) return opts;
    if (opts.some((o) => o.id === selected.id)) return opts;
    return [selected, ...opts];
  }, []);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.35 }}>
        Elegí un criterio en cualquier catálogo para cargar la tabla. La búsqueda de la tabla aplica solo
        sobre las filas de la página actual.
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
                  prioridad_categoria: String(e.target.value) as IniciadoresPendientesFilters["prioridad_categoria"],
                })
              }
              fullWidth
              options={[...PRIORIDAD_OPTIONS]}
            />
          </Box>
          <Box sx={{ ...compactFiltroSx, flex: "1 1 140px", minWidth: 128 }}>
            <AppSelect
              appearance="dense"
              label="Distrito"
              value={filters.distrito}
              onChange={(e) => onChangeFilters({ ...filters, distrito: String(e.target.value) })}
              fullWidth
              options={distritoOptions}
            />
          </Box>
          <Box sx={{ ...compactFiltroSx, flex: "2 1 200px", minWidth: 180, maxWidth: 320 }}>
            <Autocomplete<CalleCatalogoItem, false, false, false>
              size="small"
              options={mergeCalleOptions(calleValue, calleOptions)}
              getOptionLabel={(o) => o.nombre}
              isOptionEqualToValue={(a, b) => a.id === b.id}
              filterOptions={(opts) => opts}
              value={calleValue}
              inputValue={calleInput}
              onInputChange={(_, value, reason) => {
                if (reason === "input") {
                  setCalleInput(value);
                  setCalleValue(null);
                  if (filters.calle_catalogo_id != null) {
                    onChangeFilters({ ...filters, calle_catalogo_id: null });
                  }
                } else if (reason === "clear") {
                  setCalleInput("");
                  setCalleValue(null);
                  onChangeFilters({ ...filters, calle_catalogo_id: null });
                }
              }}
              onChange={(_, newVal) => {
                const opt = newVal && typeof newVal === "object" ? newVal : null;
                setCalleValue(opt);
                setCalleInput(opt?.nombre ?? "");
                onChangeFilters({ ...filters, calle_catalogo_id: opt?.id ?? null });
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Calle (catálogo)"
                  placeholder="Escribir para buscar…"
                  sx={{
                    "& .MuiInputBase-root": {
                      fontFamily: '"Tactic Sans", sans-serif',
                      fontSize: "0.875rem",
                    },
                  }}
                />
              )}
            />
          </Box>
          <Box sx={{ ...compactFiltroSx, flex: "0 1 132px", minWidth: 120 }}>
            <AppSelect
              appearance="dense"
              label="Turno"
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
        <AppButton dsVariant="secondary" dsSize="sm" onClick={onRefrescar}>
          Refrescar
        </AppButton>
      </Stack>

      {tablaVisible ? (
        <IniciadoresPendientesTableMrt
          rows={rows}
          total={total}
          page={page}
          perPage={perPage}
          loading={loading}
          selectedIds={selectedIds}
          onPageChange={onPageChange}
          onPerPageChange={onPerPageChange}
          onSelectionChange={onSelectionChange}
          onAssignSelected={onAssignSelected}
        />
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
          La tabla se mostrará cuando elijas una opción en tipo, prioridad, distrito, calle o turno.
        </Typography>
      )}
    </Box>
  );
};

export default TablaIniciadoresPendientes;
