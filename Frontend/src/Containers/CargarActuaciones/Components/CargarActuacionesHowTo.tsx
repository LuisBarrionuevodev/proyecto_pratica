import { Box, Typography } from "@mui/material";

import {
    COLORS,
    getStatusBadgeStyles,
    kbdStyles,
    legendStyles,
    legendTextStyles,
    legendTitleStyles,
} from "../styles/cargarActuacionesStyles";

/**
 * Bloque de ayuda reutilizable para la carga batch de actas (Glide).
 * Se muestra debajo de la grilla en la vista dedicada "Cargar actas".
 */
export function CargarActuacionesHowTo() {
    return (
        <Box sx={legendStyles}>
            <Typography sx={legendTitleStyles}>CÓMO USAR:</Typography>
            <Typography sx={legendTextStyles} component="div">
                <strong>1.</strong> Empieza a cargar datos: <strong>DOBLE CLICK</strong> en cualquier celda o presiona
                <span style={kbdStyles}>Enter</span> para editarla
                <br />
                <strong>2.</strong> Presiona <span style={kbdStyles}>Tab</span> para moverte entre celdas
                <br />
                <strong>3.</strong> Para agregar filas: presiona <span style={kbdStyles}>Enter</span> o haz clic en la fila
                inferior
                <br />
                <strong>4.</strong> La validación por fila es <strong>automática</strong> al editar
                <br />
                <strong>5.</strong> Para confirmar todo: usa el botón <strong>“Mandar todo”</strong>
                <br />
                <strong>6.</strong> Para borrar un dropdown: selecciona la opción vacía al inicio de la lista
                <br />
                <br />
                <strong>COLORES:</strong>{" "}
                <span style={getStatusBadgeStyles(COLORS.errorLight, COLORS.errorText)}>ERROR</span>
                <span style={getStatusBadgeStyles(COLORS.successLight, COLORS.successText)}>OK</span>
                <span style={getStatusBadgeStyles(COLORS.warningLight, COLORS.warningText)}>ADVERTENCIA</span>
                <span style={getStatusBadgeStyles("#1E2127", COLORS.white)}>PENDIENTE</span>
                <span style={getStatusBadgeStyles(COLORS.primary, COLORS.white)}>VALIDANDO</span>
            </Typography>
        </Box>
    );
}
