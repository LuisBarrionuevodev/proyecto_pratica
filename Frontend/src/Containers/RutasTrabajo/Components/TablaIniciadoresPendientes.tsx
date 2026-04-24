import { memo, useCallback, useMemo, useRef } from "react";
import { Box, Button, Chip, Stack, TextField, Typography } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_RowSelectionState,
  type MRT_TableOptions,
  type MRT_Updater,
} from "material-react-table";

import type { IRutaIniciadorPendienteRow } from "../../../api/rutasTrabajoApi";
import { distritoNombrePendiente, rubroLineaPendiente } from "../planificacion/utils/iniciadorDisplay";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { DARK_TABLE_CONFIG } from "../../Actuaciones/styles/actuacionesTableStyles";
import { filtroItemStyles } from "../../Actuaciones/styles/filtroStyles";
import { AppButton, AppSelect } from "../../../ui";
import {
  asignacionFiltroInputSlotSx,
  planificacionPanelFooterMetaSx,
  planificacionTextFieldSx,
  rutasAsignacionNeutralContainedButtonSx,
} from "../styles/institutionalVisual";

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

/** Pool Asignación: sin paginación ni ordenamiento MRT (filtros ya están fuera de la tabla). */
const ASIGNACION_INICIADORES_MRT_OPTIONS: Partial<MRT_TableOptions<IRutaIniciadorPendienteRow>> = {
  enablePagination: false,
  enableSorting: false,
  enableColumnActions: false,
  enableBottomToolbar: false,
  /** Menos nodos DOM cuando el pool tiene muchas filas (scroll virtual). */
  enableRowVirtualization: true,
};

function getIniciadorPoolRowId(row: IRutaIniciadorPendienteRow) {
  return String(row.id);
}

/** Controles de filtro alineados por línea base del input (misma “banda” visual). */
const compactFiltroSx = {
  ...filtroItemStyles,
  minWidth: 0,
  flex: "1 1 120px",
  maxWidth: 220,
  display: "flex",
  flexDirection: "column",
  justifyContent: "flex-end",
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

  const rowSelectionRef = useRef(rowSelection);
  rowSelectionRef.current = rowSelection;

  const handleRowSelectionChange = useCallback(
    (updaterOrValue: MRT_Updater<MRT_RowSelectionState>) => {
      const next =
        typeof updaterOrValue === "function" ? updaterOrValue(rowSelectionRef.current) : updaterOrValue;
      onSelectionChange(
        Object.keys(next)
          .filter((k) => next[k])
          .map(Number)
      );
    },
    [onSelectionChange]
  );

  const enableRowSelectionForRow = useCallback(
    (row: { original: IRutaIniciadorPendienteRow }) => !assignedIniciadorIds.has(row.original.id),
    [assignedIniciadorIds]
  );

  const renderTopToolbarCustomActions = useCallback(() => {
    const nSel = selectedIds.length;
    return (
      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ pl: 0.5 }} flexWrap="wrap" useFlexGap>
        <Typography sx={{ ...planificacionPanelFooterMetaSx, fontSize: "0.8125rem", color: GLASS_COLORS.textSecondary }}>
          {totalEnPool} en pool · {rows.length} visibles
        </Typography>
        <Chip label={`${nSel} seleccionados`} color="primary" variant="filled" size="small" />
        <AppButton dsVariant="primary" dsSize="sm" onClick={onAssignSelected} disabled={nSel === 0}>
          Asignar seleccionados
        </AppButton>
      </Stack>
    );
  }, [totalEnPool, rows.length, selectedIds.length, onAssignSelected]);

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
        id: "tipo_prioridad",
        header: "Tipo · Prioridad",
        size: 188,
        Cell: ({ row }) => {
          const label = row.original.badges?.tipo_label ?? row.original.tipo_iniciador;
          const cfg = prioridadCfg(row.original.prioridad);
          return (
            <Stack spacing={0.65} alignItems="flex-start" sx={{ py: 0.25, minWidth: 0 }}>
              <Chip label={label} size="small" sx={TIPO_SX} />
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
            </Stack>
          );
        },
      },
      {
        id: "domicilio",
        header: "Domicilio",
        size: 262,
        Cell: ({ row }) => {
          const orig = row.original;
          const d =
            orig.domicilio_texto ??
            `${orig.domicilio?.calle ?? "-"} ${orig.domicilio?.numero ?? ""}`.trim();
          const linea1 = d?.trim() || "—";
          const rubroTxt = rubroLineaPendiente(orig);
          const distritoTxt = distritoNombrePendiente(orig);
          const tactic = '"Tactic Sans", sans-serif' as const;
          const secundaria = {
            fontFamily: tactic,
            lineHeight: 1.28,
            wordBreak: "break-word" as const,
          };
          return (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.3, minWidth: 0, py: 0.125 }}>
              <Typography
                variant="body2"
                sx={{
                  fontSize: "0.8125rem",
                  lineHeight: 1.35,
                  color: GLASS_COLORS.textPrimary,
                  fontFamily: tactic,
                  fontWeight: 600,
                  wordBreak: "break-word",
                }}
              >
                {linea1}
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  ...secundaria,
                  fontSize: "0.7rem",
                  fontWeight: 500,
                  color:
                    distritoTxt !== "—" ? GLASS_COLORS.textSecondary : "rgba(255,255,255,0.28)",
                }}
              >
                {distritoTxt}
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  ...secundaria,
                  fontSize: "0.68rem",
                  fontWeight: 500,
                  color: rubroTxt !== "—" ? GLASS_COLORS.textMuted : "rgba(255,255,255,0.22)",
                }}
              >
                {rubroTxt}
              </Typography>
            </Box>
          );
        },
      },
    ],
    [assignedIniciadorIds]
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...ASIGNACION_INICIADORES_MRT_OPTIONS,
    columns,
    data: rows,
    getRowId: getIniciadorPoolRowId,

    enableEditing: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,

    enableRowSelection: enableRowSelectionForRow,
    enableSelectAll: false,

    state: { rowSelection },
    onRowSelectionChange: handleRowSelectionChange,

    renderTopToolbarCustomActions,
  });

  return <MaterialReactTable table={table} />;
}

const IniciadoresPoolTableMrtMemo = memo(IniciadoresPoolTableMrt);

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
function TablaIniciadoresPendientesInner({
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
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25 }}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ columnGap: 1, rowGap: 1, alignItems: "flex-end" }}>
        <Box sx={{ ...compactFiltroSx, ...asignacionFiltroInputSlotSx, flex: "1 1 140px", minWidth: 132 }}>
          <AppSelect
            appearance="dense"
            label="Tipo"
            value={filters.tipo}
            onChange={(e) => onChangeFilters({ ...filters, tipo: String(e.target.value) })}
            fullWidth
            options={[...TIPO_INICIADOR_OPTIONS]}
          />
        </Box>
        <Box sx={{ ...compactFiltroSx, ...asignacionFiltroInputSlotSx, flex: "0 1 172px", minWidth: 160 }}>
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
          <Box sx={{ ...compactFiltroSx, ...asignacionFiltroInputSlotSx, flex: "1 1 140px", minWidth: 128 }}>
            <AppSelect
              appearance="dense"
              label="Distrito"
              value={filters.distrito}
              onChange={(e) => onChangeFilters({ ...filters, distrito: String(e.target.value) })}
              fullWidth
              options={distritoOptions}
            />
          </Box>
        ) : null}
        <Box sx={{ ...compactFiltroSx, ...asignacionFiltroInputSlotSx, flex: "2 1 200px", minWidth: 160, maxWidth: 360 }}>
          <TextField
            hiddenLabel
            size="small"
            fullWidth
            placeholder="Buscar — domicilio, rubro…"
            value={filters.q}
            onChange={(e) => onChangeFilters({ ...filters, q: e.target.value })}
            inputProps={{ "aria-label": "Buscar en el listado del pool" }}
            sx={[planificacionTextFieldSx, asignacionFiltroInputSlotSx]}
          />
        </Box>
      </Stack>
      {onSincronizarDetalle ? (
        <Stack
          direction="row"
          justifyContent="flex-end"
          sx={{
            borderTop: `1px solid ${GLASS_COLORS.borderLight}`,
            pt: 1,
            mt: 0.25,
          }}
        >
          <Button
            variant="contained"
            size="small"
            disableElevation
            disabled={detailLoading}
            onClick={() => onSincronizarDetalle()}
            sx={rutasAsignacionNeutralContainedButtonSx}
          >
            {detailLoading ? "Sincronizando…" : "Sincronizar borrador"}
          </Button>
        </Stack>
      ) : null}

      <IniciadoresPoolTableMrtMemo
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

const TablaIniciadoresPendientes = memo(TablaIniciadoresPendientesInner);

export default TablaIniciadoresPendientes;
export { FILTROS_VACIOS as ASIGNACION_POOL_FILTROS_VACIOS };
