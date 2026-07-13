import { Alert, Box, Grid, Typography } from "@mui/material";
import { useMemo } from "react";
import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
  type MRT_TableOptions,
} from "material-react-table";

import type {
  IndicadorActasPorInspector,
  IndicadorInspectorNoRealizadas,
  IndicadorInspectorRealizadas,
  IndicadoresProductividadResponse,
} from "../../../api/indicadoresApi";
import { DataTableMrtShell } from "../../../components/dataTable/DataTableMrtShell";
import { dashboardEmptyStateCompactSx } from "../../../styles/DashboardStyles";
import { BANDEJA_MRT_READ_ONLY_TABLE_PROPS } from "../../Actuaciones/Components/bandejaTableCells";
import {
  COLORS,
  DARK_TABLE_CONFIG,
  MRT_READ_ONLY_BANDEJA,
} from "../../Actuaciones/styles/actuacionesTableStyles";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import { DashboardAnalyticsChartCard } from "./DashboardAnalyticsChartCard";
import { DashboardSectionBlock } from "./DashboardSectionBlock";

const PAGE_SIZE = 5;
const TABLE_MAX_HEIGHT = 280;

type Props = {
  data: IndicadoresProductividadResponse | null;
  loading: boolean;
  error: string | null;
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
      }}
    >
      {value}
    </Typography>
  );
}

function InspectorCell({ name }: { name: string }) {
  return (
    <Typography
      component="span"
      sx={{
        fontFamily: '"Tactic Sans", sans-serif',
        fontSize: "12px",
        fontWeight: 600,
        color: COLORS.white,
      }}
      title={name}
    >
      {name}
    </Typography>
  );
}

function baseTableOptions<T extends { inspector_id: number }>(
  columns: MRT_ColumnDef<T>[],
  data: T[],
  emptyMessage: string,
  defaultSortId: string
): MRT_TableOptions<T> {
  return {
    ...DARK_TABLE_CONFIG,
    ...BANDEJA_MRT_READ_ONLY_TABLE_PROPS,
    ...MRT_READ_ONLY_BANDEJA,
    columns,
    data,
    getRowId: (row) => String(row.inspector_id),
    enableRowActions: false,
    enableRowSelection: false,
    enableColumnFilters: true,
    enableGlobalFilter: false,
    enableSorting: true,
    enablePagination: true,
    enableDensityToggle: false,
    enableFullScreenToggle: false,
    enableHiding: false,
    enableColumnActions: false,
    layoutMode: "semantic",
    muiTopToolbarProps: {
      sx: { minHeight: 32, px: 0, py: 0 },
    },
    muiTablePaperProps: {
      elevation: 0,
      sx: { background: "transparent", overflow: "hidden" },
    },
    muiTableContainerProps: {
      sx: {
        maxHeight: TABLE_MAX_HEIGHT,
        overflowX: { xs: "auto", md: "hidden" },
      },
    },
    initialState: {
      density: "compact",
      pagination: { pageSize: PAGE_SIZE, pageIndex: 0 },
      sorting: [{ id: defaultSortId, desc: true }],
    },
    renderEmptyRowsFallback: () => (
      <Box sx={{ ...dashboardEmptyStateCompactSx, py: 2 }}>{emptyMessage}</Box>
    ),
  };
}

function RealizadasTable({ rows }: { rows: IndicadorInspectorRealizadas[] }) {
  const columns = useMemo<MRT_ColumnDef<IndicadorInspectorRealizadas>[]>(
    () => [
      {
        accessorKey: "inspector",
        header: "Inspector",
        size: 140,
        grow: true,
        Cell: ({ cell }) => <InspectorCell name={String(cell.getValue() ?? "")} />,
      },
      {
        accessorKey: "total_realizadas",
        header: "Total",
        size: 56,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "inspecciones",
        header: "Insp.",
        size: 48,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_oficio",
        header: "R. of.",
        size: 48,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_notificacion",
        header: "R. notif.",
        size: 56,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "denuncias",
        header: "Den.",
        size: 44,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
    ],
    []
  );

  const table = useMaterialReactTable(
    baseTableOptions(
      columns,
      rows,
      "Sin actuaciones realizadas por inspector en el período.",
      "total_realizadas"
    )
  );

  return (
    <DashboardAnalyticsChartCard title="Actuaciones realizadas por inspector">
      <DataTableMrtShell loadingMode="none">
        <MaterialReactTable table={table} />
      </DataTableMrtShell>
    </DashboardAnalyticsChartCard>
  );
}

function NoRealizadasTable({ rows }: { rows: IndicadorInspectorNoRealizadas[] }) {
  const columns = useMemo<MRT_ColumnDef<IndicadorInspectorNoRealizadas>[]>(
    () => [
      {
        accessorKey: "inspector",
        header: "Inspector",
        size: 140,
        grow: true,
        Cell: ({ cell }) => <InspectorCell name={String(cell.getValue() ?? "")} />,
      },
      {
        accessorKey: "total_no_realizadas",
        header: "Total",
        size: 56,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "inspecciones",
        header: "Insp.",
        size: 48,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_oficio",
        header: "R. of.",
        size: 48,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_notificacion",
        header: "R. notif.",
        size: 56,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "denuncias",
        header: "Den.",
        size: 44,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
    ],
    []
  );

  const table = useMaterialReactTable(
    baseTableOptions(
      columns,
      rows,
      "Sin actuaciones no realizadas por inspector en el período.",
      "total_no_realizadas"
    )
  );

  return (
    <DashboardAnalyticsChartCard title="Actuaciones no realizadas por inspector">
      <DataTableMrtShell loadingMode="none">
        <MaterialReactTable table={table} />
      </DataTableMrtShell>
    </DashboardAnalyticsChartCard>
  );
}

function ActasTable({ rows }: { rows: IndicadorActasPorInspector[] }) {
  const columns = useMemo<MRT_ColumnDef<IndicadorActasPorInspector>[]>(
    () => [
      {
        accessorKey: "inspector",
        header: "Inspector",
        size: 140,
        grow: true,
        Cell: ({ cell }) => <InspectorCell name={String(cell.getValue() ?? "")} />,
      },
      {
        accessorKey: "notificacion",
        header: "Notif.",
        size: 56,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "comprobacion",
        header: "Compr.",
        size: 56,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "clausura",
        header: "Claus.",
        size: 52,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "decomiso",
        header: "Decom.",
        size: 52,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "total_actas",
        header: "Total",
        size: 56,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
    ],
    []
  );

  const table = useMaterialReactTable(
    baseTableOptions(
      columns,
      rows,
      "Sin actas labradas por inspector en el período.",
      "total_actas"
    )
  );

  return (
    <DashboardAnalyticsChartCard title="Actas labradas por inspector">
      <DataTableMrtShell loadingMode="none">
        <MaterialReactTable table={table} />
      </DataTableMrtShell>
    </DashboardAnalyticsChartCard>
  );
}

/**
 * Productividad por inspector desde `/api/indicadores/productividad`.
 */
export function DashboardProductividadSection({ data, error }: Props) {
  const realizadas = data?.inspectores_realizadas ?? [];
  const noRealizadas = data?.inspectores_no_realizadas ?? [];
  const actas = data?.actas_por_inspector ?? [];

  return (
    <DashboardSectionBlock title="Productividad">
      {error ? (
        <Alert severity="warning" sx={{ ...alertBaseStyles, mb: 1.25 }}>
          {error}
        </Alert>
      ) : null}

      <Grid container spacing={1.5}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <RealizadasTable rows={realizadas} />
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <NoRealizadasTable rows={noRealizadas} />
        </Grid>
        <Grid size={{ xs: 12 }}>
          <ActasTable rows={actas} />
        </Grid>
      </Grid>
    </DashboardSectionBlock>
  );
}
