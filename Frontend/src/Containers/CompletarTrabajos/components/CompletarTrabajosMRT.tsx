import { useMemo } from "react";
import { Box, IconButton, Tooltip, Typography } from "@mui/material";
import AssignmentTurnedInIcon from "@mui/icons-material/AssignmentTurnedIn";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { formatActuacionListDomicilioLinea } from "../../../utils/formatDomicilioLineaVisible";
import {
  BandejaDomicilioYRubroCell,
  BandejaEllipsisCell,
  BandejaFechaYChipOtCell,
  BandejaSegmentChipsCell,
  BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
  splitCommaList,
} from "../../Actuaciones/Components/bandejaTableCells";
import {
  COLORS,
  DARK_TABLE_CONFIG,
} from "../../Actuaciones/styles/actuacionesTableStyles";
import { tipoIniciadorDesdeCodigoApi } from "../../RutasTrabajo/planificacion/utils/iniciadorDisplay";
import { DataTableMrtShell } from "../../../components/dataTable/DataTableMrtShell";

function domicilioLinea(row: ICompletarTrabajoPendienteRow): string {
  const t =
    row.domicilio_texto?.trim() || formatActuacionListDomicilioLinea(row).trim() || "";
  return t || "—";
}

function inspectoresNombres(row: ICompletarTrabajoPendienteRow): string[] {
  const texto = row.inspectores_texto?.trim();
  if (texto) return splitCommaList(texto);
  return [row.inspector1, row.inspector2, row.inspector3].filter((s): s is string =>
    Boolean(s?.trim())
  );
}

function origenTipoSegments(row: ICompletarTrabajoPendienteRow): string[] {
  const segs: string[] = [];
  const origenLabel = tipoIniciadorDesdeCodigoApi(row.tipo_iniciador);
  const tipo = (row.tipo_actuacion ?? "").trim();
  if (origenLabel) segs.push(`Origen: ${origenLabel}`);
  if (tipo) segs.push(`Tipo: ${tipo}`);
  return segs;
}

function origenTipoAccessor(row: ICompletarTrabajoPendienteRow): string {
  return origenTipoSegments(row).join(" · ") || "—";
}

function equipoSegments(row: ICompletarTrabajoPendienteRow): string[] {
  const segs: string[] = [];
  const grupo = (row.grupo_nombre ?? "").trim();
  if (grupo) segs.push(`Grupo: ${grupo}`);
  segs.push(...inspectoresNombres(row));
  return segs;
}

function domicilioAccessor(row: ICompletarTrabajoPendienteRow): string {
  const parts = [domicilioLinea(row), (row.rubro_nombre ?? "").trim(), (row.nombre_local ?? "").trim()].filter(
    Boolean
  );
  return parts.join(" · ") || "—";
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
 * Columnas compuestas F3.11a (referencia Actuaciones / Comprobación).
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
        id: "col_fecha_ot",
        header: "Fecha · OT",
        accessorFn: (row) =>
          [row.fecha_actuacion ?? "", row.orden_trabajo_numero ?? ""].filter(Boolean).join(" "),
        size: 118,
        grow: false,
        Cell: ({ row }) => {
          const r = row.original;
          const fecha = (r.fecha_actuacion ?? "").trim() || "—";
          const ot = (r.orden_trabajo_numero ?? "").trim();
          return <BandejaFechaYChipOtCell fecha={fecha} ot={ot} />;
        },
      },
      {
        id: "col_origen_tipo",
        header: "Origen · tipo",
        accessorFn: origenTipoAccessor,
        size: 168,
        grow: true,
        Cell: ({ row }) => {
          const segs = origenTipoSegments(row.original);
          if (segs.length === 0) {
            return <BandejaEllipsisCell value="—" />;
          }
          return <BandejaSegmentChipsCell segments={segs} />;
        },
      },
      {
        id: "col_domicilio",
        header: "Domicilio",
        accessorFn: domicilioAccessor,
        size: 200,
        grow: true,
        Cell: ({ row }) => {
          const r = row.original;
          const line = domicilioLinea(r);
          const nombreLocal = (r.nombre_local ?? "").trim();
          const rubro = r.rubro_nombre;
          if (!nombreLocal) {
            return <BandejaDomicilioYRubroCell domicilioLinea={line} rubro={rubro} />;
          }
          return (
            <Tooltip
              title={`${line}${nombreLocal ? ` · ${nombreLocal}` : ""}`}
              placement="top-start"
              enterDelay={400}
            >
              <Box sx={{ maxWidth: "100%" }}>
                <BandejaDomicilioYRubroCell domicilioLinea={line} rubro={rubro} />
              </Box>
            </Tooltip>
          );
        },
      },
      {
        id: "col_equipo",
        header: "Equipo",
        accessorFn: (row) => equipoSegments(row).join(", "),
        size: 156,
        grow: true,
        Cell: ({ row }) => <BandejaSegmentChipsCell segments={equipoSegments(row.original)} />,
      },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...DARK_TABLE_CONFIG,
    ...BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
    enableEditing: false,
    enableRowSelection: false,
    enableSelectAll: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enablePagination: true,
    enableSorting: true,
    layoutMode: "grid",
    muiTableContainerProps: {
      sx: {
        ...((DARK_TABLE_CONFIG.muiTableContainerProps as { sx?: object })?.sx ?? {}),
        maxHeight: "calc(100vh - 280px)",
      },
    },
    columns,
    data: rows,
    getRowId: (r) => String(r.ruta_item_id),
    enableRowActions: true,
    positionActionsColumn: "first",
    displayColumnDefOptions: {
      "mrt-row-actions": {
        size: 52,
        grow: false,
      },
    },
    manualPagination: true,
    rowCount: total,
    state: {
      pagination,
      isLoading: loading,
      showProgressBars: loading,
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
            color: COLORS.white,
            transition: "color 0.2s ease, background-color 0.2s ease",
            "&:hover": {
              color: COLORS.primary,
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
    <DataTableMrtShell
      loading={loading}
      loadingMode="progress"
      footer={
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
      }
    >
      <MaterialReactTable table={table} />
    </DataTableMrtShell>
  );
}
