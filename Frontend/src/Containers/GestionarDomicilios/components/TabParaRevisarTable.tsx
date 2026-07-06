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
import { sliceSupportsNomenclaturaEdit } from "../domicilioSliceTabs";
import type { DomicilioPendienteItem, DomiciliosSlice } from "../types";
import { buildParaRevisarColumns } from "./domicilioGestionSharedColumns";

interface TabParaRevisarTableProps {
  items: DomicilioPendienteItem[];
  loading: boolean;
  emptyMessage: string;
  onGeolocalizar?: (item: DomicilioPendienteItem) => void;
  onEditNomenclatura?: (item: DomicilioPendienteItem) => void;
}

function needsNomenclaturaAction(item: DomicilioPendienteItem): boolean {
  const slice = item.slice as DomiciliosSlice | undefined;
  if (slice) return sliceSupportsNomenclaturaEdit(slice);
  return (
    item.nomenclatura_estado === "NOMENCLATURA_PENDIENTE" ||
    item.calle_status === "PENDIENTE" ||
    item.calle_status === "REVIEW"
  );
}

const TabParaRevisarTable = ({
  items,
  loading,
  emptyMessage,
  onGeolocalizar,
  onEditNomenclatura,
}: TabParaRevisarTableProps) => {
  const columns = useMemo<MRT_ColumnDef<DomicilioPendienteItem>[]>(
    () => buildParaRevisarColumns(),
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
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => undefined,
      sx: {
        cursor: "default",
      },
    }),
    renderEmptyRowsFallback: () => (
      <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
        {emptyMessage}
      </Typography>
    ),
    enableRowActions: !!(onGeolocalizar || onEditNomenclatura),
    positionActionsColumn: "last",
    displayColumnDefOptions: {
      "mrt-row-actions": {
        header: "Acciones",
        size: 180,
      },
    },
    renderRowActions: ({ row }) => {
      const item = row.original;
      const showNom = needsNomenclaturaAction(item) && !!onEditNomenclatura;
      const showGeo = !!onGeolocalizar;
      return (
        <>
          {showNom ? (
            <AppButton
              dsVariant="secondary"
              dsSize="sm"
              onClick={() => onEditNomenclatura!(item)}
              sx={{ ...exportButtonStyles, mr: 0.5 }}
            >
              Nomenclatura
            </AppButton>
          ) : null}
          {showGeo ? (
            <AppButton
              dsVariant="secondary"
              dsSize="sm"
              onClick={() => onGeolocalizar!(item)}
              sx={exportButtonStyles}
            >
              Geolocalizar
            </AppButton>
          ) : null}
        </>
      );
    },
  });

  return (
    <DataTableMrtShell loading={loading} loadingMode="progress">
      <MaterialReactTable table={table} />
    </DataTableMrtShell>
  );
};

export default TabParaRevisarTable;
