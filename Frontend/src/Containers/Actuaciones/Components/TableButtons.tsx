import { Box, Button } from "@mui/material";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import { TableExportBoxStyles, TableExportButtonStyles } from "../../../styles/TablasStyle";
import { exportVisibleRows, exportAllData } from "../../../utils/exportToCsv";

export const TablaExportButtons = ({ data, table }: { data: any[], table: any }) => (
    <Box sx={TableExportBoxStyles}>
        <Button onClick={() => exportAllData(data)} startIcon={<FileDownloadIcon />} sx={TableExportButtonStyles}>
            Exportar todo
        </Button>
        <Button
            disabled={!table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()}
            onClick={() => exportVisibleRows(table.getSelectedRowModel().rows, table)}
            startIcon={<FileDownloadIcon />}
            sx={TableExportButtonStyles}
        >
            Exportar seleccionados
        </Button>
        <Button
            disabled={table.getRowModel().rows.length === 0}
            onClick={() => exportVisibleRows(table.getRowModel().rows, table)}
            startIcon={<FileDownloadIcon />}
            sx={TableExportButtonStyles}
        >
            Exportar página
        </Button>
    </Box>
);
