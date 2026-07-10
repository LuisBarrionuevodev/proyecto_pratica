import AddLocationAltIcon from "@mui/icons-material/AddLocationAlt";
import EditLocationAltIcon from "@mui/icons-material/EditLocationAlt";
import { Chip, IconButton, Stack, Tooltip, Typography } from "@mui/material";
import {
  MaterialReactTable,
  type MRT_ColumnDef,
  type MRT_PaginationState,
  useMaterialReactTable,
} from "material-react-table";
import { useMemo } from "react";
import type { GestionDomiciliosRow } from "../../../../../api/gestionDomiciliosApi";
import { DataTableMrtShell } from "../../../../../components/dataTable/DataTableMrtShell";
import { AppButton } from "../../../../../ui";
import { exportButtonStyles } from "../../../../Actuaciones/styles/actuacionesTableStyles";
import { GESTION_DOMICILIOS_MRT_GLASS_BASE } from "../mapaDomiciliosMrtGlassBase";
import { labelGeoChip } from "../mapaDomiciliosOperativoFilters";

export type MapaDomiciliosGeolocalizacionActionVariant = "button" | "icon";
export type MapaDomiciliosGeolocalizacionListaLayoutVariant = "default" | "mapa";

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
  actionVariant?: MapaDomiciliosGeolocalizacionActionVariant;
  layoutVariant?: MapaDomiciliosGeolocalizacionListaLayoutVariant;
};

export function MapaDomiciliosGeolocalizacionLista({
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
  actionVariant = "button",
  layoutVariant = "default",
}: Props) {
  const useIconActions = actionVariant === "icon";
  const isMapaLayout = layoutVariant === "mapa";

  const columns = useMemo<MRT_ColumnDef<GestionDomiciliosRow>[]>(() => {
    const domicilioColumn: MRT_ColumnDef<GestionDomiciliosRow> = useIconActions
      ? {
          accessorKey: "domicilio_linea",
          header: "Domicilio",
          size: 220,
          Cell: ({ row }) => (
            <Stack spacing={0.5} sx={{ py: 0.25 }}>
              <Typography variant="body2" sx={{ lineHeight: 1.35 }}>
                {row.original.domicilio_linea}
              </Typography>
              <Chip
                size="small"
                label={labelGeoChip(row.original.geo_chip)}
                color={row.original.geo_chip === "EN_MAPA" ? "primary" : "warning"}
                variant={row.original.geo_chip === "EN_MAPA" ? "filled" : "outlined"}
                sx={{ alignSelf: "flex-start" }}
              />
            </Stack>
          ),
        }
      : {
          accessorKey: "domicilio_linea",
          header: "Domicilio",
          size: 220,
        };

    const base: MRT_ColumnDef<GestionDomiciliosRow>[] = [domicilioColumn];

    if (!useIconActions) {
      base.push({
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
      });
    }

    return base;
  }, [useIconActions]);

  const table = useMaterialReactTable({
    ...GESTION_DOMICILIOS_MRT_GLASS_BASE,
    columns,
    data: rows,
    enableEditing: false,
    enableRowSelection: false,
    enableTopToolbar: false,
    enableGlobalFilter: false,
    enableColumnFilters: false,
    enableHiding: false,
    enableDensityToggle: false,
    enableFullScreenToggle: false,
    enableSorting: false,
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
    muiTableContainerProps: {
      sx: {
        overflowX: "hidden",
        maxWidth: "100%",
        ...(isMapaLayout ? { maxHeight: "none", flex: "none" } : {}),
      },
    },
    muiTablePaperProps: {
      sx: {
        overflow: "hidden",
        maxWidth: "100%",
        ...(isMapaLayout ? { boxShadow: "none", backgroundImage: "none" } : {}),
      },
    },
    muiBottomToolbarProps: isMapaLayout
      ? {
          sx: {
            minHeight: 48,
            "& .MuiTablePagination-root": { overflow: "hidden" },
          },
        }
      : undefined,
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
        size: useIconActions ? 72 : 130,
      },
    },
    renderRowActions: ({ row }) => {
      const item = row.original;
      const enMapa = item.geo_chip === "EN_MAPA";

      if (useIconActions) {
        return (
          <Tooltip title={enMapa ? "Reubicar" : "Geolocalizar"}>
            <IconButton
              size="small"
              color="primary"
              aria-label={enMapa ? "Reubicar domicilio" : "Geolocalizar domicilio"}
              onClick={(e) => {
                e.stopPropagation();
                if (enMapa) onReubicar(item);
                else onGeolocalizar(item);
              }}
            >
              {enMapa ? <EditLocationAltIcon fontSize="small" /> : <AddLocationAltIcon fontSize="small" />}
            </IconButton>
          </Tooltip>
        );
      }

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
