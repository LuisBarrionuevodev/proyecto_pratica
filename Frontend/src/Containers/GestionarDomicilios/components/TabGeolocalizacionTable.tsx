import { Button } from "@mui/material";
import {
  MaterialReactTable,
  type MRT_ColumnDef,
  useMaterialReactTable,
} from "material-react-table";
import { useMemo } from "react";
import { formatDomicilioLineaVisible } from "../../../utils/formatDomicilioLineaVisible";
import { TablePendientesStyle } from "../../../styles/MapStyles";
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
    ...TablePendientesStyle,
    columns,
    data: items,
    enableEditing: false,
    state: { isLoading: loading },
    enableRowActions: true,
    positionActionsColumn: "last",
    renderRowActions: ({ row }) => (
      <Button size="small" onClick={() => onGeolocalizar(row.original)}>
        Geolocalizar
      </Button>
    ),
  });

  return <MaterialReactTable table={table} />;
};

export default TabGeolocalizacionTable;
