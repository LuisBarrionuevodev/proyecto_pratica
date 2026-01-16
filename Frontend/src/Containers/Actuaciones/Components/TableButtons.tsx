/**
 * Botones de exportación para la tabla de Actuaciones
 * Estilo Neo-Brutalista oscuro
 */

import { Box, Button } from "@mui/material";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import { exportVisibleRows, exportAllData } from "../../../utils/exportToCsv";
import { exportBoxStyles, exportButtonStyles } from "../styles/actuacionesTableStyles";

export const TablaExportButtons = ({ data, table }: { data: any[], table: any }) => (
    <Box sx={exportBoxStyles}>
        <Button
            onClick={() => exportAllData(data)}
            startIcon={<FileDownloadIcon />}
            sx={exportButtonStyles}
        >
            Exportar todo
        </Button>
        <Button
            disabled={!table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()}
            onClick={() => exportVisibleRows(table.getSelectedRowModel().rows, table)}
            startIcon={<FileDownloadIcon />}
            sx={exportButtonStyles}
        >
            Exportar seleccionados
        </Button>
        <Button
            disabled={table.getRowModel().rows.length === 0}
            onClick={() => exportVisibleRows(table.getRowModel().rows, table)}
            startIcon={<FileDownloadIcon />}
            sx={exportButtonStyles}
        >
            Exportar página
        </Button>
    </Box>
);
