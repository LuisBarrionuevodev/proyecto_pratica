import { Button } from "@mui/material";
import {
  MaterialReactTable,
  type MRT_ColumnDef,
  useMaterialReactTable,
} from "material-react-table";
import { useMemo } from "react";
import { TablePendientesStyle } from "../../../styles/MapStyles";
import type { DomicilioPendienteItem } from "../types";

interface TabGeolocalizacionTableProps {
  items: DomicilioPendienteItem[];
  loading: boolean;
  onGeolocalizar: (item: DomicilioPendienteItem) => void;
}

const formatDireccion = (item: DomicilioPendienteItem) => {
  const numero = item.numero || item.numero_raw || "";
  if (item.numero_tipo === "ESQUINA" && item.esquina_normalizada) {
    return `${item.calle_normalizada || item.calle_raw || ""} y ${item.esquina_normalizada}`;
  }
  return `${item.calle_normalizada || item.calle_raw || ""} ${numero}`.trim();
};

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
        Cell: ({ row }) => formatDireccion(row.original),
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
