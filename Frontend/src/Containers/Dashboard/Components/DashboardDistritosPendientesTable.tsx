import { Box, Typography } from "@mui/material";
import { useMemo } from "react";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_TableOptions,
} from "material-react-table";

import type { IndicadoresDistritoPendientesItem } from "../../../api/indicadoresApi";
import { DataTableMrtShell } from "../../../components/dataTable/DataTableMrtShell";
import { dashboardEmptyStateCompactSx } from "../../../styles/DashboardStyles";
import { BANDEJA_MRT_READ_ONLY_TABLE_PROPS } from "../../Actuaciones/Components/bandejaTableCells";
import {
  COLORS,
  DARK_TABLE_CONFIG,
  MRT_READ_ONLY_BANDEJA,
} from "../../Actuaciones/styles/actuacionesTableStyles";

const DEFAULT_PAGE_SIZE = 10;
const TABLE_MIN_HEIGHT = 220;
const TABLE_MAX_HEIGHT = 380;
const EMPTY_MSG = "Sin pendientes agrupados por distrito.";

type DistritoPendientesRow = IndicadoresDistritoPendientesItem & {
  distrito_label: string;
};

type Props = {
  rows: IndicadoresDistritoPendientesItem[];
};

function NumericCell({ value }: { value: number }) {
  return (
    <Typography
      component="span"
      sx={{
        display: "block",
        textAlign: "right",
        fontFamily: '"Tactic Sans", sans-serif',
        fontSize: "12px",
        fontWeight: 600,
        color: COLORS.white,
        whiteSpace: "nowrap",
      }}
    >
      {value}
    </Typography>
  );
}

function DistritoCell({ label }: { label: string }) {
  return (
    <Typography
      component="span"
      sx={{
        fontFamily: '"Tactic Sans", sans-serif',
        fontSize: "12px",
        fontWeight: 600,
        color: COLORS.white,
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
        display: "block",
        maxWidth: "100%",
      }}
      title={label}
    >
      {label}
    </Typography>
  );
}

function baseTableOptions(
  columns: MRT_ColumnDef<DistritoPendientesRow>[],
  data: DistritoPendientesRow[]
): MRT_TableOptions<DistritoPendientesRow> {
  return {
    ...DARK_TABLE_CONFIG,
    ...BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
    ...MRT_READ_ONLY_BANDEJA,
    columns,
    data,
    getRowId: (row) => String(row.distrito_id),
    enableRowActions: false,
    enableRowSelection: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enableSorting: true,
    enablePagination: data.length > DEFAULT_PAGE_SIZE,
    enableDensityToggle: false,
    enableFullScreenToggle: false,
    enableHiding: false,
    enableColumnActions: false,
    layoutMode: "grid",
    muiTopToolbarProps: {
      sx: { display: "none" },
    },
    muiBottomToolbarProps: {
      sx: {
        minHeight: 36,
        "& .MuiTablePagination-root": { color: COLORS.white },
      },
    },
    muiTablePaperProps: {
      elevation: 0,
      sx: { background: "transparent", overflow: "hidden" },
    },
    muiTableContainerProps: {
      sx: {
        minHeight: TABLE_MIN_HEIGHT,
        maxHeight: TABLE_MAX_HEIGHT,
        overflowX: "auto",
      },
    },
    muiTableHeadCellProps: {
      sx: {
        whiteSpace: "nowrap",
        fontSize: "11px",
        py: 0.75,
      },
    },
    initialState: {
      density: "compact",
      pagination: { pageSize: DEFAULT_PAGE_SIZE, pageIndex: 0 },
      sorting: [{ id: "total", desc: true }],
    },
    renderEmptyRowsFallback: () => (
      <Box sx={{ ...dashboardEmptyStateCompactSx, py: 2 }}>{EMPTY_MSG}</Box>
    ),
  };
}

/**
 * Tabla read-only MRT de pendientes actuales por distrito (mismo patrón que Productividad).
 */
export function DashboardDistritosPendientesTable({ rows }: Props) {
  const data = useMemo<DistritoPendientesRow[]>(
    () =>
      rows.map((row) => ({
        ...row,
        distrito_label: row.distrito_codigo
          ? `${row.distrito_nombre} (${row.distrito_codigo})`
          : row.distrito_nombre,
      })),
    [rows]
  );

  const columns = useMemo<MRT_ColumnDef<DistritoPendientesRow>[]>(
    () => [
      {
        accessorKey: "distrito_label",
        header: "Distrito",
        size: 180,
        minSize: 140,
        Cell: ({ cell }) => <DistritoCell label={String(cell.getValue() ?? "")} />,
      },
      {
        accessorKey: "total",
        header: "Total",
        size: 64,
        minSize: 56,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Total pendientes" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "relevamientos",
        header: "Relev.",
        size: 72,
        minSize: 64,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Relevamientos" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_oficio",
        header: "Reins. oficio",
        size: 88,
        minSize: 80,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Reinspecciones por oficio" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_notificacion",
        header: "Reins. notif.",
        size: 88,
        minSize: 80,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Reinspecciones por notificación" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
    ],
    []
  );

  const table = useMaterialReactTable(baseTableOptions(columns, data));

  return (
    <DataTableMrtShell loadingMode="none">
      <MaterialReactTable table={table} />
    </DataTableMrtShell>
  );
}
