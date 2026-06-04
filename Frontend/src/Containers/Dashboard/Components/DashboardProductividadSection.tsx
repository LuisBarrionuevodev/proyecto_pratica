import { Alert, Box, Chip, Grid, Typography } from "@mui/material";
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
import { dashboardEmptyStateCompactSx, dashboardGlassCardSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { BANDEJA_MRT_READ_ONLY_TABLE_PROPS } from "../../Actuaciones/Components/bandejaTableCells";
import {
  COLORS,
  DARK_TABLE_CONFIG,
  MRT_READ_ONLY_BANDEJA,
} from "../../Actuaciones/styles/actuacionesTableStyles";
import { alertBaseStyles } from "../../Actuaciones/styles/filtroStyles";
import { DashboardSectionBlock } from "./DashboardSectionBlock";

const PAGE_SIZE = 5;
const TABLE_MAX_HEIGHT = 280;

type Props = {
  data: IndicadoresProductividadResponse | null;
  loading: boolean;
  error: string | null;
};

function isNoHuboLabel(label: string): boolean {
  const n = label.trim().toUpperCase().replace(/_/g, " ");
  return n === "NO HUBO" || n === "NOHUBO";
}

function displayChipLabel(raw: string | null | undefined): string | null {
  const t = (raw ?? "").trim();
  if (!t || t === "—" || t.toLowerCase() === "sin datos" || isNoHuboLabel(t)) {
    return null;
  }
  return t;
}

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

function DiscreteChip({ label }: { label: string | null }) {
  if (!label) {
    return (
      <Typography variant="caption" sx={{ color: GLASS_COLORS.textMuted }}>
        —
      </Typography>
    );
  }
  return (
    <Chip
      size="small"
      variant="outlined"
      label={label}
      sx={{
        maxWidth: "100%",
        height: 22,
        fontFamily: '"Tactic Sans", sans-serif',
        fontSize: "0.7rem",
        fontWeight: 600,
        color: GLASS_COLORS.textSecondary,
        borderColor: GLASS_COLORS.borderLight,
        "& .MuiChip-label": { px: 0.75 },
      }}
    />
  );
}

function tableShellSx() {
  return {
    ...dashboardGlassCardSx,
    p: { xs: 0.75, sm: 1 },
    minWidth: 0,
    overflow: "hidden",
    overflowX: "auto",
  };
}

function baseTableOptions<T extends { inspector_id: number }>(
  columns: MRT_ColumnDef<T>[],
  data: T[],
  loading: boolean,
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
    enableGlobalFilter: true,
    enableSorting: true,
    enablePagination: true,
    layoutMode: "grid",
    muiTableContainerProps: {
      sx: {
        maxHeight: TABLE_MAX_HEIGHT,
      },
    },
    initialState: {
      density: "compact",
      pagination: { pageSize: PAGE_SIZE, pageIndex: 0 },
      sorting: [{ id: defaultSortId, desc: true }],
    },
    state: {
      isLoading: loading,
      showProgressBars: loading,
    },
    renderEmptyRowsFallback: () => (
      <Box sx={{ ...dashboardEmptyStateCompactSx, py: 2 }}>{emptyMessage}</Box>
    ),
  };
}

function RealizadasTable({
  rows,
  loading,
}: {
  rows: IndicadorInspectorRealizadas[];
  loading: boolean;
}) {
  const columns = useMemo<MRT_ColumnDef<IndicadorInspectorRealizadas>[]>(
    () => [
      {
        accessorKey: "inspector",
        header: "Inspector",
        size: 160,
        Cell: ({ cell }) => <InspectorCell name={String(cell.getValue() ?? "")} />,
      },
      {
        accessorKey: "total_realizadas",
        header: "Total realizadas",
        size: 110,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "inspecciones",
        header: "Inspecciones",
        size: 95,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_oficio",
        header: "Reins. oficio",
        size: 95,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_notificacion",
        header: "Reins. notificación",
        size: 115,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "denuncias",
        header: "Denuncias",
        size: 85,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "tipo_principal",
        header: "Tipo principal",
        size: 130,
        Cell: ({ cell }) => <DiscreteChip label={displayChipLabel(String(cell.getValue() ?? ""))} />,
      },
    ],
    []
  );

  const table = useMaterialReactTable(
    baseTableOptions(
      columns,
      rows,
      loading,
      "Sin actuaciones realizadas por inspector en el período.",
      "total_realizadas"
    )
  );

  return (
    <Box sx={tableShellSx()}>
      <Typography
        variant="caption"
        sx={{
          display: "block",
          mb: 0.75,
          fontFamily: '"Tactic Sans", sans-serif',
          fontWeight: 600,
          color: GLASS_COLORS.textMuted,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontSize: "0.65rem",
        }}
      >
        Actuaciones realizadas por inspector
      </Typography>
      <DataTableMrtShell loading={loading} loadingMode="progress">
        <MaterialReactTable table={table} />
      </DataTableMrtShell>
    </Box>
  );
}

function NoRealizadasTable({
  rows,
  loading,
}: {
  rows: IndicadorInspectorNoRealizadas[];
  loading: boolean;
}) {
  const columns = useMemo<MRT_ColumnDef<IndicadorInspectorNoRealizadas>[]>(
    () => [
      {
        accessorKey: "inspector",
        header: "Inspector",
        size: 160,
        Cell: ({ cell }) => <InspectorCell name={String(cell.getValue() ?? "")} />,
      },
      {
        accessorKey: "total_no_realizadas",
        header: "Total no realizadas",
        size: 120,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "contraproducencia_principal",
        header: "Contraproducencia principal",
        size: 150,
        Cell: ({ cell }) => (
          <DiscreteChip label={displayChipLabel(String(cell.getValue() ?? ""))} />
        ),
      },
      {
        accessorKey: "inspecciones",
        header: "Inspecciones",
        size: 95,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_oficio",
        header: "Reins. oficio",
        size: 95,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "reinspecciones_notificacion",
        header: "Reins. notificación",
        size: 115,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "denuncias",
        header: "Denuncias",
        size: 85,
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
      loading,
      "Sin actuaciones no realizadas por inspector en el período.",
      "total_no_realizadas"
    )
  );

  return (
    <Box sx={tableShellSx()}>
      <Typography
        variant="caption"
        sx={{
          display: "block",
          mb: 0.75,
          fontFamily: '"Tactic Sans", sans-serif',
          fontWeight: 600,
          color: GLASS_COLORS.textMuted,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontSize: "0.65rem",
        }}
      >
        Actuaciones no realizadas por inspector
      </Typography>
      <DataTableMrtShell loading={loading} loadingMode="progress">
        <MaterialReactTable table={table} />
      </DataTableMrtShell>
    </Box>
  );
}

function ActasTable({
  rows,
  loading,
}: {
  rows: IndicadorActasPorInspector[];
  loading: boolean;
}) {
  const columns = useMemo<MRT_ColumnDef<IndicadorActasPorInspector>[]>(
    () => [
      {
        accessorKey: "inspector",
        header: "Inspector",
        size: 180,
        Cell: ({ cell }) => <InspectorCell name={String(cell.getValue() ?? "")} />,
      },
      {
        accessorKey: "notificacion",
        header: "Notificación",
        size: 100,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "comprobacion",
        header: "Comprobación",
        size: 105,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "clausura",
        header: "Clausura",
        size: 85,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "decomiso",
        header: "Decomiso",
        size: 85,
        muiTableBodyCellProps: { align: "right" },
        muiTableHeadCellProps: { align: "right" },
        Cell: ({ cell }) => <NumericCell value={Number(cell.getValue() ?? 0)} />,
      },
      {
        accessorKey: "total_actas",
        header: "Total actas",
        size: 95,
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
      loading,
      "Sin actas labradas por inspector en el período.",
      "total_actas"
    )
  );

  return (
    <Box sx={tableShellSx()}>
      <Typography
        variant="caption"
        sx={{
          display: "block",
          mb: 0.75,
          fontFamily: '"Tactic Sans", sans-serif',
          fontWeight: 600,
          color: GLASS_COLORS.textMuted,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontSize: "0.65rem",
        }}
      >
        Actas labradas por inspector
      </Typography>
      <DataTableMrtShell loading={loading} loadingMode="progress">
        <MaterialReactTable table={table} />
      </DataTableMrtShell>
    </Box>
  );
}

/**
 * Productividad por inspector desde `/api/indicadores/productividad`.
 */
export function DashboardProductividadSection({ data, loading, error }: Props) {
  const sectionLoading = loading && !data;
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
          <RealizadasTable rows={realizadas} loading={sectionLoading} />
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <NoRealizadasTable rows={noRealizadas} loading={sectionLoading} />
        </Grid>
        <Grid size={{ xs: 12 }}>
          <ActasTable rows={actas} loading={sectionLoading} />
        </Grid>
      </Grid>
    </DashboardSectionBlock>
  );
}
