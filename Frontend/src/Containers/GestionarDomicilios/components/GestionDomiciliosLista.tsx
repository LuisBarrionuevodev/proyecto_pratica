import { Chip, Typography } from "@mui/material";
import {
  MaterialReactTable,
  type MRT_ColumnDef,
  type MRT_PaginationState,
  useMaterialReactTable,
} from "material-react-table";
import { useMemo } from "react";
import type { GestionDomiciliosRow } from "../../../api/gestionDomiciliosApi";
import { DataTableMrtShell } from "../../../components/dataTable/DataTableMrtShell";
import { AppButton } from "../../../ui";
import { exportButtonStyles } from "../../Actuaciones/styles/actuacionesTableStyles";
import { GESTION_DOMICILIOS_MRT_GLASS_BASE } from "../gestionarDomiciliosMrtGlassBase";
import { labelGeoChip } from "../gestionDomiciliosOperativoFilters";

type Props = {
  rows: GestionDomiciliosRow[];
  loading: boolean;
  emptyMessage: string;
  selectedId: number | null;
  totalRows: number;
  pagination: MRT_PaginationState;
  onPaginationChange: (next: MRT_PaginationState) => void;
  onSelectRow: (row: GestionDomiciliosRow) => void;
  onGeolocalizar: (row: GestionDomiciliosRow) => void;
  onReubicar: (row: GestionDomiciliosRow) => void;
};

export function GestionDomiciliosLista({
  rows,
  loading,
  emptyMessage,
  selectedId,
  totalRows,
  pagination,
  onPaginationChange,
  onSelectRow,
  onGeolocalizar,
  onReubicar,
}: Props) {
  const columns = useMemo<MRT_ColumnDef<GestionDomiciliosRow>[]>(
    () => [
      {
        accessorKey: "domicilio_linea",
        header: "Domicilio",
        size: 220,
      },
      {
        accessorKey: "geo_chip",
        header: "Estado",
        size: 120,
        Cell: ({ row }) => (
          <Chip
            size="small"
            label={labelGeoChip(row.original.geo_chip)}
            color={row.original.geo_chip === "EN_MAPA" ? "primary" : "warning"}
            variant={row.original.geo_chip === "EN_MAPA" ? "filled" : "outlined"}
          />
        ),
      },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...GESTION_DOMICILIOS_MRT_GLASS_BASE,
    columns,
    data: rows,
    enableEditing: false,
    enableRowSelection: false,
    manualPagination: true,
    rowCount: totalRows,
    onPaginationChange: (updater) => {
      const next = typeof updater === "function" ? updater(pagination) : updater;
      onPaginationChange(next);
    },
    state: {
      isLoading: loading,
      showProgressBars: loading,
      pagination,
    },
    initialState: { density: "compact" },
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => onSelectRow(row.original),
      selected: row.original.domicilio_id === selectedId,
      sx: {
        cursor: "pointer",
        backgroundColor:
          row.original.domicilio_id === selectedId ? "rgba(255, 152, 0, 0.12)" : undefined,
      },
    }),
    renderEmptyRowsFallback: () => (
      <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
        {emptyMessage}
      </Typography>
    ),
    enableRowActions: true,
    positionActionsColumn: "last",
    displayColumnDefOptions: {
      "mrt-row-actions": {
        header: "Acción",
        size: 130,
      },
    },
    renderRowActions: ({ row }) => {
      const item = row.original;
      const enMapa = item.geo_chip === "EN_MAPA";
      return (
        <AppButton
          dsVariant="secondary"
          dsSize="sm"
          onClick={(e) => {
            e.stopPropagation();
            if (enMapa) onReubicar(item);
            else onGeolocalizar(item);
          }}
          sx={exportButtonStyles}
        >
          {enMapa ? "Reubicar" : "Geolocalizar"}
        </AppButton>
      );
    },
  });

  return (
    <DataTableMrtShell>
      <MaterialReactTable table={table} />
    </DataTableMrtShell>
  );
}
