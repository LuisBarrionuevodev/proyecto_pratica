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

interface TabGeolocalizacionTableProps {
  items: DomicilioPendienteItem[];
  loading: boolean;
  emptyMessage: string;
  onGeolocalizar: (item: DomicilioPendienteItem) => void;
}

const TabGeolocalizacionTable = ({
  items,
  loading,
  emptyMessage,
  onGeolocalizar,
}: TabGeolocalizacionTableProps) => {
  const columns = useMemo<MRT_ColumnDef<DomicilioPendienteItem>[]>(
    () => buildDomicilioDisplayColumns(),
    []
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
    enableRowActions: true,
    positionActionsColumn: "last",
    displayColumnDefOptions: {
      "mrt-row-actions": {
        header: "Acciones",
        size: 130,
      },
    },
    renderRowActions: ({ row }) => (
      <AppButton
        dsVariant="secondary"
        dsSize="sm"
        onClick={() => onGeolocalizar(row.original)}
        sx={exportButtonStyles}
      >
        Geolocalizar
      </AppButton>
    ),
  });

  return (
    <DataTableMrtShell loading={loading} loadingMode="progress">
      <MaterialReactTable table={table} />
    </DataTableMrtShell>
  );
};

export default TabGeolocalizacionTable;
