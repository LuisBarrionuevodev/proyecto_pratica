import {
  MaterialReactTable,
  type MRT_ColumnDef,
  useMaterialReactTable,
} from "material-react-table";
import { useMemo } from "react";
import { formatDomicilioLineaVisible } from "../../../utils/formatDomicilioLineaVisible";
import { DataTableMrtShell } from "../../../components/dataTable/DataTableMrtShell";
import { exportButtonStyles } from "../../Actuaciones/styles/actuacionesTableStyles";
import { BandejaEllipsisCell } from "../../Actuaciones/Components/bandejaTableCells";
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
      { accessorKey: "domicilio_id", header: "ID", size: 80, Cell: ({ cell }) => <BandejaEllipsisCell value={String(cell.getValue() ?? "—")} /> },
      {
        accessorKey: "direccion",
        header: "Dirección",
        size: 240,
        Cell: ({ row }) => <BandejaEllipsisCell value={formatDomicilioLineaVisible(row.original) || "—"} />,
      },
      { accessorKey: "score", header: "Score", size: 80, Cell: ({ cell }) => <BandejaEllipsisCell value={String(cell.getValue() ?? "—")} /> },
      { accessorKey: "quality", header: "Quality", size: 100, Cell: ({ cell }) => <BandejaEllipsisCell value={String(cell.getValue() ?? "—")} /> },
      { accessorKey: "geo_status", header: "Status", size: 120, Cell: ({ cell }) => <BandejaEllipsisCell value={String(cell.getValue() ?? "—")} /> },
    ],
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
    enableRowActions: true,
    positionActionsColumn: "last",
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
