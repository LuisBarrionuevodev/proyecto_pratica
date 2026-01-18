import { Box, Typography } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import FilterListIcon from "@mui/icons-material/FilterList";
import ViewColumnIcon from "@mui/icons-material/ViewColumn";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";

import {
    legendStyles,
    legendTitleStyles,
    legendTextStyles,
    COLORS,
} from "../styles/actuacionesTableStyles";

export const GridLegend = () => {
    return (
        <Box sx={legendStyles}>
            <Typography sx={legendTitleStyles}>
                 CÓMO USAR LA GESTIÓN DE ACTUACIONES:
            </Typography>
            <Typography sx={legendTextStyles} component="div">
                Esta vista está destinada a la gestión de actuaciones, donde puedes editar y eliminar (con cuidado) registros existentes.
                <br />
                <br />
                <strong>Funcionalidades principales:</strong>
                <ul style={{ margin: "8px 0", paddingLeft: "20px" }}>
                    <li style={{ marginBottom: "8px" }}>
                        <SearchIcon sx={{ color: COLORS.white, verticalAlign: "middle", mr: 0.5, fontSize: 18 }} />
                        <strong>BUSCAR:</strong> Utiliza el campo de búsqueda global para encontrar actuaciones por cualquier campo.
                    </li>
                    <li style={{ marginBottom: "8px" }}>
                        <FilterListIcon sx={{ color: COLORS.white, verticalAlign: "middle", mr: 0.5, fontSize: 18 }} />
                        <strong>FILTRAR:</strong> Haz clic en el icono de filtro en cada columna para filtrar de manera personalizada por campo.
                    </li>
                    <li style={{ marginBottom: "8px" }}>
                        <ViewColumnIcon sx={{ color: COLORS.white, verticalAlign: "middle", mr: 0.5, fontSize: 18 }} />
                        <strong>COLUMNAS:</strong> Usa el botón de columnas para ocultar o mostrar campos según necesites.
                    </li>
                    <li style={{ marginBottom: "8px" }}>
                        <FileDownloadIcon sx={{ color: COLORS.white, verticalAlign: "middle", mr: 0.5, fontSize: 18 }} />
                        <strong>EXPORTAR:</strong> Exporta todas las actuaciones, solo las seleccionadas, o la página actual a un archivo Excel.
                    </li>
                    <li style={{ marginBottom: "8px" }}>
                        <EditIcon sx={{ color: COLORS.white, verticalAlign: "middle", mr: 0.5, fontSize: 18 }} />
                        <strong>EDITAR:</strong> Haz doble clic en cualquier celda para editar su contenido.
                    </li>
                    <li style={{ marginBottom: "8px" }}>
                        <DeleteIcon sx={{ color: COLORS.white, verticalAlign: "middle", mr: 0.5, fontSize: 18 }} />
                        <strong>ELIMINAR:</strong> Utiliza el botón de la papelera en cada fila para eliminar una actuación. ¡Ten cuidado, esta acción es permanente!
                    </li>
                </ul>
                <br />
                <span style={{ color: COLORS.warning, fontWeight: 700 }}>
                    ⚠️ Advertencia: Las eliminaciones son permanentes y no se pueden deshacer.
                </span>
            </Typography>
        </Box>
    );
};
