/**
 * Estilos específicos para CargarRelevamientos
 * Tabla ajustada al ancho de columnas (sin espacio vacío a la derecha)
 */

import { GLASS_COLORS } from "../../../styles/GlassStyles";

// =============================================================================
// PALETA DE COLORES
// =============================================================================
export const COLORS = {
    primary: "#0166FF",
    white: "#FFFFFF",
    grayDark: "#2B2E34",
    border: "#3a3d44",
};

// Ancho calculado de las columnas:
// Fecha(140) + Inspector(200) + Calle(200) + Numero(120) + Rubro(180) + Contraproducencia(200) = 1040px
// + rowMarker (~50px) = ~1090px
const TABLE_WIDTH = 1100;

// =============================================================================
// CONTENEDORES
// =============================================================================
export const containerStyles = {
    width: "100%",
    height: "100%",
    fontFamily: '"Tactic Sans", sans-serif',
};

// Wrapper sin centrar - contenido alineado a la izquierda
export const wrapperStyles = {
    width: "100%",
    height: "89%",
    display: "flex",
    padding: { xs: 2, sm: 3 },
    boxSizing: "border-box",
    flexDirection: "column" as const,
};

// =============================================================================
// CONTENEDOR DE GRILLA - Ancho fijo basado en columnas
// =============================================================================
export const gridContainerStyles = {
    border: `1px solid ${COLORS.border}`,
    borderRadius: "8px",
    overflow: "hidden",
    backgroundImage: "linear-gradient(rgba(255, 255, 255, 0.069), rgba(255, 255, 255, 0.069))",
    backgroundColor: COLORS.grayDark,
    width: "1074px",
    height: "480px",
    maxWidth: "100%",
    maxHeight: "100%", // Responsive: no excede el contenedor padre
};

// =============================================================================
// BOTÓN MANDAR TODO - Azul cuando activo
// =============================================================================
export const buttonMandarTodoStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 600,
    fontSize: "14px",
    textTransform: "none" as const,
    borderRadius: "8px",
    padding: "10px 24px",
    transition: "all 0.2s ease",
    backgroundColor: COLORS.primary,
    color: COLORS.white,
    border: `1px solid ${COLORS.primary}`,
    "&:hover": {
        backgroundColor: "#0155DD",
    },
    "&.Mui-disabled": {
        backgroundColor: "rgba(255, 255, 255, 0.08)",
        color: "rgba(255, 255, 255, 0.3)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
    },
};
