import { Typography } from "@mui/material";
import {
  MaterialReactTable,
  type MRT_ColumnDef,
  useMaterialReactTable,
} from "material-react-table";
import { useMemo } from "react";
import { DataTableMrtShell } from "../../../components/dataTable/DataTableMrtShell";
import { exportButtonStyles } from "../../Actuaciones/styles/actuacionesTableStyles";
import { AppButton } from "../../../ui";
import { GESTION_DOMICILIOS_MRT_GLASS_BASE } from "../gestionarDomiciliosMrtGlassBase";
import type { DomicilioPendienteItem } from "../types";
import { buildDomicilioDisplayColumns } from "./domicilioGestionSharedColumns";

interface TabDomiciliosOverviewTableProps {
  items: DomicilioPendienteItem[];
  loading: boolean;
  emptyMessage: string;
  showGeoAction?: boolean;
  showErrorDetail?: boolean;
  onGeolocalizar?: (item: DomicilioPendienteItem) => void;
}

const TabDomiciliosOverviewTable = ({
  items,
  loading,
  emptyMessage,
  showGeoAction = false,
  showErrorDetail = false,
  onGeolocalizar,
}: TabDomiciliosOverviewTableProps) => {
  const columns = useMemo<MRT_ColumnDef<DomicilioPendienteItem>[]>(
    () => buildDomicilioDisplayColumns({ showErrorDetail }),
    [showErrorDetail]
  );

  const table = useMaterialReactTable({
    ...GESTION_DOMICILIOS_MRT_GLASS_BASE,
    columns,
    data: items,
    enableEditing: false,
    enableRowSelection: false,
    state: { isLoading: loading, showProgressBars: loading },
    initialState: { density: "compact" },
    renderEmptyRowsFallback: () => (
      <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
        {emptyMessage}
      </Typography>
    ),
    enableRowActions: showGeoAction && !!onGeolocalizar,
    positionActionsColumn: "last",
    displayColumnDefOptions: showGeoAction
      ? {
          "mrt-row-actions": {
            header: "Acciones",
            size: 130,
          },
        }
      : undefined,
    renderRowActions:
      showGeoAction && onGeolocalizar
        ? ({ row }) => (
            <AppButton
              dsVariant="secondary"
              dsSize="sm"
              onClick={() => onGeolocalizar(row.original)}
              sx={exportButtonStyles}
            >
              Geolocalizar
            </AppButton>
          )
        : undefined,
  });

  return (
    <DataTableMrtShell loading={loading} loadingMode="progress">
      <MaterialReactTable table={table} />
    </DataTableMrtShell>
  );
};

export default TabDomiciliosOverviewTable;
