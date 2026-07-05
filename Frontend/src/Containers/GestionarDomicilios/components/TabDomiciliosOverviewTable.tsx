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
import { buildDomicilioClasificacionColumns } from "./domicilioGestionSharedColumns";

interface TabDomiciliosOverviewTableProps {
  items: DomicilioPendienteItem[];
  loading: boolean;
  showGeoAction?: boolean;
  onGeolocalizar?: (item: DomicilioPendienteItem) => void;
}

const TabDomiciliosOverviewTable = ({
  items,
  loading,
  showGeoAction = false,
  onGeolocalizar,
}: TabDomiciliosOverviewTableProps) => {
  const columns = useMemo<MRT_ColumnDef<DomicilioPendienteItem>[]>(
    () => [
      ...buildDomicilioClasificacionColumns(),
      {
        accessorKey: "error_msg",
        header: "Error / detalle",
        size: 200,
        Cell: ({ cell }) => String(cell.getValue() ?? "—"),
      },
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
    enableRowActions: showGeoAction && !!onGeolocalizar,
    positionActionsColumn: "last",
    renderRowActions: showGeoAction && onGeolocalizar
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
