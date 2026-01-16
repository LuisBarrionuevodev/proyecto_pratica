/**
 * Componente de leyenda con instrucciones de uso
 * Muestra cómo usar la grilla y los colores de estado
 */

import { Box, Typography } from "@mui/material";
import {
    legendStyles,
    legendTitleStyles,
    legendTextStyles,
    kbdStyles,
    getStatusBadgeStyles,
    COLORS,
} from "../styles/cargarActuacionesStyles";

// =============================================================================
// COMPONENTE
// =============================================================================

/**
 * Leyenda de instrucciones de uso de la grilla
 * Incluye atajos de teclado y significado de colores
 */
export function GridLegend() {
    return (
        <Box sx={legendStyles}>
            <Typography sx={legendTitleStyles}>
                📝 CÓMO USAR:
            </Typography>
            <Typography sx={legendTextStyles} component="div">
                <strong>1.</strong> Empieza a cargar datos: <strong>DOBLE CLICK</strong> en cualquier celda o presiona 
                <span style={kbdStyles}>Enter</span> para editarla<br/>
                <strong>2.</strong> Presiona <span style={kbdStyles}>Tab</span> para moverte entre celdas<br/>
                <strong>3.</strong> Para agregar filas: presiona <span style={kbdStyles}>Enter</span> o haz clic en la fila inferior<br/>
                <strong>4.</strong> Las filas se validan y guardan <strong>automáticamente</strong><br/>
                <br/>
                <strong>COLORES:</strong>{" "}
                <span style={getStatusBadgeStyles("#5C2323", "#FF6B6B")}>
                    ERROR
                </span>
                <span style={getStatusBadgeStyles("#1E3D2F", "#4ADE80")}>
                    OK
                </span>
                <span style={getStatusBadgeStyles("#3D2E1E", "#FFB86C")}>
                    ADVERTENCIA
                </span>
                <span style={getStatusBadgeStyles("#1E2127", COLORS.white)}>
                    PENDIENTE
                </span>
            </Typography>
        </Box>
    );
}

export default GridLegend;
