import { Box, Button } from "@mui/material";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import type { MRT_ColumnDef, MRT_TableInstance } from "material-react-table";
import { TableExportBoxStyles, TableExportButtonStyles } from "../../../styles/TablasStyle";
import { exportMrtRowsToXlsx } from "../../../utils/exportToXlsx";

type TablaExportButtonsProps = {
  table: MRT_TableInstance<any>;
  filePrefix?: string;
  data?: any[];
};

const buildFileName = (prefix: string) => {
  const date = new Date().toISOString().slice(0, 10);
  return `${prefix}_${date}.xlsx`;
};

const getVisibleColumnsInOrder = (table: MRT_TableInstance<any>): MRT_ColumnDef<any>[] => {
  const leafColumns = table.getAllLeafColumns();
  const visibleColumns = leafColumns.filter((col) => col.getIsVisible());
  return visibleColumns.map((col) => col.columnDef);
};

export const TablaExportButtons = ({
  table,
  filePrefix = "actuaciones",
}: TablaExportButtonsProps) => (
  <Box sx={TableExportBoxStyles}>
    <Button
      onClick={() =>
        exportMrtRowsToXlsx({
          rows: table.getPrePaginationRowModel().rows,
          columns: getVisibleColumnsInOrder(table),
          fileName: buildFileName(filePrefix),
          sheetName: "Datos",
        })
      }
      startIcon={<FileDownloadIcon />}
      sx={TableExportButtonStyles}
    >
      Exportar todo
    </Button>
    <Button
      disabled={!table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()}
      onClick={() =>
        exportMrtRowsToXlsx({
          rows: table.getSelectedRowModel().rows,
          columns: getVisibleColumnsInOrder(table),
          fileName: buildFileName(filePrefix),
          sheetName: "Datos",
        })
      }
      startIcon={<FileDownloadIcon />}
      sx={TableExportButtonStyles}
    >
      Exportar seleccionados
    </Button>
    <Button
      disabled={table.getRowModel().rows.length === 0}
      onClick={() =>
        exportMrtRowsToXlsx({
          rows: table.getRowModel().rows,
          columns: getVisibleColumnsInOrder(table),
          fileName: buildFileName(filePrefix),
          sheetName: "Datos",
        })
      }
      startIcon={<FileDownloadIcon />}
      sx={TableExportButtonStyles}
    >
      Exportar página
    </Button>
  </Box>
);
