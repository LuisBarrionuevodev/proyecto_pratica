import { Box } from "@mui/material";
import {
  MaterialReactTable,
  type MRT_ColumnDef,
  useMaterialReactTable,
} from "material-react-table";
import { useMemo } from "react";
import { formatDomicilioLineaVisible } from "../../../utils/formatDomicilioLineaVisible";
import { dataTableShellSx, DATA_TABLE_MRT_GLASS_COLORS } from "../../../styles/mrtGlassDataTablePreset";
import { AppButton } from "../../../ui";
import { GESTION_DOMICILIOS_MRT_GLASS_BASE } from "../gestionarDomiciliosMrtGlassBase";
import type { DomicilioPendienteItem } from "../types";

interface TabGeolocalizacionTableProps {
  items: DomicilioPendienteItem[];
  loading: boolean;
  onGeolocalizar: (item: DomicilioPendienteItem) => void;
}

const TabGeolocalizacionTable = ({
  items,
  loading,
  onGeolocalizar,
}: TabGeolocalizacionTableProps) => {
  const columns = useMemo<MRT_ColumnDef<DomicilioPendienteItem>[]>(
    () => [
      { accessorKey: "domicilio_id", header: "ID", size: 80 },
      {
        accessorKey: "direccion",
        header: "Dirección",
        size: 240,
        Cell: ({ row }) => formatDomicilioLineaVisible(row.original),
      },
      { accessorKey: "score", header: "Score", size: 80 },
      { accessorKey: "quality", header: "Quality", size: 100 },
      { accessorKey: "geo_status", header: "Status", size: 120 },
    ],
    []
  );

  const table = useMaterialReactTable({
    ...GESTION_DOMICILIOS_MRT_GLASS_BASE,
    columns,
    data: items,
    enableEditing: false,
    enableRowSelection: false,
    state: { isLoading: loading },
    enableRowActions: true,
    positionActionsColumn: "last",
    renderRowActions: ({ row }) => (
      <AppButton
        dsVariant="secondary"
        dsSize="sm"
        onClick={() => onGeolocalizar(row.original)}
        sx={{
          fontFamily: '"Tactic Sans", sans-serif',
          textTransform: "none",
          fontSize: "12px",
          fontWeight: 600,
          borderColor: DATA_TABLE_MRT_GLASS_COLORS.border,
          color: DATA_TABLE_MRT_GLASS_COLORS.white,
          "&:hover": {
            borderColor: DATA_TABLE_MRT_GLASS_COLORS.primary,
            color: DATA_TABLE_MRT_GLASS_COLORS.primary,
          },
        }}
      >
        Geolocalizar
      </AppButton>
    ),
  });

  return (
    <Box sx={dataTableShellSx}>
      <MaterialReactTable table={table} />
    </Box>
  );
};

export default TabGeolocalizacionTable;
