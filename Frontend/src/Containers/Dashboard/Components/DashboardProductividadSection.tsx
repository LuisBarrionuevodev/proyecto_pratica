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

const DEFAULT_PAGE_SIZE = 10;
const TABLE_MIN_HEIGHT = 220;
const TABLE_MAX_HEIGHT = 380;

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
        whiteSpace: "nowrap",
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
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
        display: "block",
        maxWidth: "100%",
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
        size: 160,
        minSize: 140,
        Cell: ({ cell }) => <InspectorCell name={String(cell.getValue() ?? "")} />,
      },
      {
        accessorKey: "total_realizadas",
        header: "Total",
        size: 64,
        minSize: 56,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Total realizadas" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "inspecciones",
        header: "Inspección",
        size: 72,
        minSize: 64,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Inspecciones" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_oficio",
        header: "Reins. oficio",
        size: 80,
        minSize: 72,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Reinspecciones por oficio" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_notificacion",
        header: "Reins. notif.",
        size: 84,
        minSize: 76,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Reinspecciones por notificación" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "denuncias",
        header: "Denuncias",
        size: 72,
        minSize: 64,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Denuncias" },
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
        minSize: 120,
        Cell: ({ cell }) => <InspectorCell name={String(cell.getValue() ?? "")} />,
      },
      {
        accessorKey: "total_no_realizadas",
        header: "Total",
        size: 56,
        minSize: 48,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Total no realizadas" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "contraproducencia_principal",
        header: "Contraproducencia",
        size: 120,
        minSize: 100,
        muiTableHeadCellProps: { title: "Contraproducencia principal" },
        Cell: ({ cell }) => (
          <Typography
            component="span"
            sx={{
              fontFamily: '"Tactic Sans", sans-serif',
              fontSize: "11px",
              color: COLORS.white,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              display: "block",
            }}
            title={String(cell.getValue() ?? "")}
          >
            {String(cell.getValue() ?? "—")}
          </Typography>
        ),
      },
      {
        accessorKey: "inspecciones",
        header: "Inspección",
        size: 68,
        minSize: 60,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Inspecciones" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_oficio",
        header: "Reins. oficio",
        size: 76,
        minSize: 68,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Reinspecciones por oficio" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_notificacion",
        header: "Reins. notif.",
        size: 80,
        minSize: 72,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Reinspecciones por notificación" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "denuncias",
        header: "Denuncias",
        size: 68,
        minSize: 60,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Denuncias" },
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
        size: 160,
        minSize: 140,
        Cell: ({ cell }) => <InspectorCell name={String(cell.getValue() ?? "")} />,
      },
      {
        accessorKey: "notificacion",
        header: "Notificación",
        size: 80,
        minSize: 72,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Actas de notificación" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "comprobacion",
        header: "Comprobación",
        size: 88,
        minSize: 80,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Actas de comprobación" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "clausura",
        header: "Clausura",
        size: 72,
        minSize: 64,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Actas de clausura" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "decomiso",
        header: "Decomiso",
        size: 72,
        minSize: 64,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Actas de decomiso" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "total_actas",
        header: "Total",
        size: 64,
        minSize: 56,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right", title: "Total actas labradas" },
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
        <Grid size={{ xs: 12, xl: 6 }}>
          <RealizadasTable rows={realizadas} />
        </Grid>
        <Grid size={{ xs: 12, xl: 6 }}>
          <NoRealizadasTable rows={noRealizadas} />
        </Grid>
        <Grid size={{ xs: 12 }}>
          <ActasTable rows={actas} />
        </Grid>
      </Grid>
    </DashboardSectionBlock>
  );
}
