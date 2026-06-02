import {
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnDef,
} from "material-react-table";
import { Box, Typography } from "@mui/material";
import { useMemo } from "react";

import type { IndicadoresRankingInspector } from "../../../api/indicadoresApi";
import { DARK_TABLE_CONFIG } from "../../Actuaciones/styles/actuacionesTableStyles";
import { dataTableShellSx } from "../../../styles/mrtGlassDataTablePreset";
import { dashboardEmptyStateCompactSx } from "../../../styles/DashboardStyles";

type RankingRow = IndicadoresRankingInspector & { posicion: number };

type Props = {
  items: IndicadoresRankingInspector[];
};

const RankingInspectores = ({ items }: Props) => {
  const ranking = useMemo<RankingRow[]>(
    () =>
      items.map((item, index) => ({
        ...item,
        posicion: index + 1,
      })),
    [items]
  );

  const columns = useMemo<MRT_ColumnDef<RankingRow>[]>(
    () => [
      { accessorKey: "posicion", header: "#", size: 48 },
      { accessorKey: "inspector_nombre", header: "Inspector" },
      { accessorKey: "total_actuaciones", header: "Actuaciones" },
    ],
    []
  );

  const table = useMaterialReactTable({
    columns,
    data: ranking,
    ...DARK_TABLE_CONFIG,
    enableEditing: false,
    enableRowSelection: false,
    enableSelectAll: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enableSorting: false,
    enableTopToolbar: false,
    enableBottomToolbar: ranking.length > 8,
    muiTableContainerProps: {
      sx: {
        maxHeight: Math.min(320, Math.max(160, ranking.length * 40 + 48)),
      },
    },
  });

  if (!items.length) {
    return (
      <Box sx={dashboardEmptyStateCompactSx}>
        <Typography variant="body2">Sin actuaciones con inspectores en el periodo.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={dataTableShellSx}>
      <MaterialReactTable table={table} />
    </Box>
  );
};

export default RankingInspectores;
