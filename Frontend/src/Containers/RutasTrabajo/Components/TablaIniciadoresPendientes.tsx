import { memo, useCallback, useMemo, useRef, useState } from "react";
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
import { detalleOperativoTexto } from "../utils/iniciadorDetalleOperativo";
import {
  ASIGNACION_COL_DETALLE_OPERATIVO,
  ASIGNACION_COL_DOMICILIO_RUBRO,
  ASIGNACION_COL_TIPO_PRIORIDAD,
  domicilioLineaAsignacion,
  prioridadDisplayOperativo,
  rubroLineaAsignacion,
  tipoLabelOperativo,
} from "../utils/asignacionTableDisplay";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { DARK_TABLE_CONFIG } from "../../Actuaciones/styles/actuacionesTableStyles";
import { filtroItemStyles } from "../../Actuaciones/styles/filtroStyles";
import { AppButton, AppSelect } from "../../../ui";
import {
  asignacionFiltroInputSlotSx,
  planificacionPanelFooterMetaSx,
  planificacionTextFieldSx,
  rutasAsignacionNeutralContainedButtonSx,
  rutasOperativaChipSx,
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

const TIPO_TEXT_SX = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontSize: "0.8125rem",
  fontWeight: 600,
  lineHeight: 1.35,
  color: GLASS_COLORS.textPrimary,
  wordBreak: "break-word",
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
  poolIdByIniciadorId?: Record<number, number>;
  onEliminarDelPool?: (poolIds: number[]) => void | Promise<void>;
};

type MrtProps = Omit<
  TableProps,
  "filters" | "onChangeFilters" | "distritoOptions" | "onSincronizarDetalle" | "detailLoading"
>;

function IniciadoresPoolTableMrt({
  rows,
  totalEnPool,
  selectedIds,
  assignedIniciadorIds,
  onSelectionChange,
  onAssignSelected,
  poolIdByIniciadorId,
  onEliminarDelPool,
}: MrtProps) {
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

  const [eliminandoPool, setEliminandoPool] = useState(false);

  const handleEliminarDelPool = useCallback(async () => {
    if (!onEliminarDelPool || !poolIdByIniciadorId) return;
    const poolIds = selectedIds
      .map((id) => poolIdByIniciadorId[id])
      .filter((pid): pid is number => pid != null);
    if (!poolIds.length) return;
    setEliminandoPool(true);
    try {
      await onEliminarDelPool(poolIds);
    } finally {
      setEliminandoPool(false);
    }
  }, [onEliminarDelPool, poolIdByIniciadorId, selectedIds]);

  const renderTopToolbarCustomActions = useCallback(() => {
    const nSel = selectedIds.length;
    const puedeEliminar =
      nSel > 0 &&
      Boolean(onEliminarDelPool && poolIdByIniciadorId) &&
      selectedIds.every(
        (id) => !assignedIniciadorIds.has(id) && poolIdByIniciadorId![id] != null
      );

    return (
      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ pl: 0.5 }} flexWrap="wrap" useFlexGap>
        <Typography sx={{ ...planificacionPanelFooterMetaSx, fontSize: "0.8125rem", color: GLASS_COLORS.textSecondary }}>
          {totalEnPool} en pool · {rows.length} visibles
        </Typography>
        <Chip label={`${nSel} seleccionados`} color="primary" variant="filled" size="small" />
        {onEliminarDelPool ? (
          <AppButton
            dsVariant="danger"
            dsSize="sm"
            disabled={!puedeEliminar || eliminandoPool}
            onClick={() => void handleEliminarDelPool()}
            data-testid="asignacion-eliminar-del-pool"
          >
            {eliminandoPool ? "Eliminando…" : "Eliminar del pool"}
          </AppButton>
        ) : null}
        <AppButton dsVariant="primary" dsSize="sm" onClick={onAssignSelected} disabled={nSel === 0}>
          Asignar seleccionados
        </AppButton>
      </Stack>
    );
  }, [
    totalEnPool,
    rows.length,
    selectedIds,
    assignedIniciadorIds,
    onAssignSelected,
    onEliminarDelPool,
    poolIdByIniciadorId,
    eliminandoPool,
    handleEliminarDelPool,
  ]);

  const columns = useMemo<MRT_ColumnDef<IRutaIniciadorPendienteRow>[]>(
    () => [
      {
        id: "tipo_prioridad",
        header: ASIGNACION_COL_TIPO_PRIORIDAD,
        size: 196,
        Cell: ({ row }) => {
          const tipo = tipoLabelOperativo(row.original);
          const prioridad = prioridadDisplayOperativo(row.original);
          return (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.45, minWidth: 0, py: 0.125 }}>
              <Typography variant="body2" sx={TIPO_TEXT_SX}>
                {tipo}
              </Typography>
              {prioridad ? (
                <Chip
                  label={prioridad.label}
                  size="small"
                  variant="outlined"
                  sx={{
                    ...rutasOperativaChipSx,
                    alignSelf: "flex-start",
                    height: 24,
                    backgroundColor: prioridad.bg,
                    color: prioridad.color,
                    borderColor: prioridad.color,
                    "& .MuiChip-label": {
                      fontWeight: 700,
                      color: prioridad.color,
                    },
                  }}
                />
              ) : (
                <Typography
                  variant="caption"
                  sx={{ color: GLASS_COLORS.textMuted, fontFamily: '"Tactic Sans", sans-serif' }}
                >
                  —
                </Typography>
              )}
            </Box>
          );
        },
      },
      {
        id: "detalle_operativo",
        header: ASIGNACION_COL_DETALLE_OPERATIVO,
        size: 280,
        Cell: ({ row }) => {
          const detalle = detalleOperativoTexto(row.original);
          if (!detalle) {
            return (
              <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted }}>
                —
              </Typography>
            );
          }
          return (
            <Typography
              variant="caption"
              title={detalle}
              sx={{
                fontFamily: '"Tactic Sans", sans-serif',
                color: GLASS_COLORS.textSecondary,
                lineHeight: 1.35,
                display: "-webkit-box",
                WebkitLineClamp: 3,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
                wordBreak: "break-word",
              }}
            >
              {detalle}
            </Typography>
          );
        },
      },
      {
        id: "domicilio_rubro",
        header: ASIGNACION_COL_DOMICILIO_RUBRO,
        size: 240,
        Cell: ({ row }) => {
          const domicilio = domicilioLineaAsignacion(row.original);
          const rubro = rubroLineaAsignacion(row.original);
          const tactic = '"Tactic Sans", sans-serif' as const;
          return (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.35, minWidth: 0, py: 0.125 }}>
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
                {domicilio}
              </Typography>
              {rubro ? (
                <Typography
                  variant="caption"
                  sx={{
                    fontFamily: tactic,
                    fontSize: "0.7rem",
                    fontWeight: 500,
                    lineHeight: 1.28,
                    color: GLASS_COLORS.textMuted,
                    wordBreak: "break-word",
                  }}
                >
                  {rubro}
                </Typography>
              ) : (
                <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.22)", fontFamily: tactic }}>
                  —
                </Typography>
              )}
            </Box>
          );
        },
      },
    ],
    []
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
  poolIdByIniciadorId,
  onEliminarDelPool,
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
        poolIdByIniciadorId={poolIdByIniciadorId}
        onEliminarDelPool={onEliminarDelPool}
      />
    </Box>
  );
}

const TablaIniciadoresPendientes = memo(TablaIniciadoresPendientesInner);

export default TablaIniciadoresPendientes;
export { FILTROS_VACIOS as ASIGNACION_POOL_FILTROS_VACIOS };
