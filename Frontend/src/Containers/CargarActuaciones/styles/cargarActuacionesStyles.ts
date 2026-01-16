/**
 * Estilos Neo-Brutalistas para CargarActuaciones
 * Basado en el sistema de diseño "Neo Amidst" con estética Neo-Brutalismo
 * Integra estilos base de TablasStyle.ts
 */

import type { Theme } from "@glideapps/glide-data-grid";
import { TableGeneralStyles, TableTitleStyles } from "../../../styles/TablasStyle";

// =============================================================================
// PALETA DE COLORES NEO-BRUTALISTA
// =============================================================================

export const COLORS = {
    // Colores primarios
    primary: "#0166FF",          // Azul principal (acento)
    black: "#000000",            // Negro puro para bordes y sombras
    white: "#FFFFFF",            // Blanco puro para fondos
    
    // Grises
    grayDark: "#2B2E34",         // Gris oscuro (navbar, headers tabla)
    grayMedium: "#353535",       // Gris medio (bordes)
    grayLight: "#D9D9D9",        // Gris claro (inputs)
    grayLighter: "#F5F5F5",      // Gris muy claro (fondos secundarios)
    
    // Estados
    success: "#2D9F4B",          // Verde éxito
    successLight: "#E8F5E9",     // Verde claro fondo
    error: "#E53935",            // Rojo error
    errorLight: "#FFEBEE",       // Rojo claro fondo
    warning: "#FF9800",          // Naranja advertencia
    warningLight: "#FFF3E0",     // Naranja claro fondo
    
    // Grupos de columnas - Todos usan grayDark para consistencia
    groupBlue: "#2B2E34",        // Headers grupo Actuación
    groupPurple: "#2B2E34",      // Headers grupo Inspectores
    groupOrange: "#2B2E34",      // Headers grupo Establecimiento
    groupGreen: "#2B2E34",       // Headers grupo Actas
    groupYellow: "#2B2E34",      // Headers grupo Reinspección
    groupPink: "#2B2E34",        // Headers grupo Expediente
} as const;

// =============================================================================
// SOMBRAS NEO-BRUTALISTAS (sin blur, offset directo)
// =============================================================================

export const SHADOWS = {
    hard: "6px 6px 0px #000000",
    hardSmall: "4px 4px 0px #000000",
    hardHover: "8px 8px 0px #000000",
    pressed: "2px 2px 0px #000000",
    none: "none",
} as const;

// =============================================================================
// ESTILOS DEL CONTENEDOR (extendidos de TablasStyle)
// =============================================================================

/** Estilos del contenedor principal */
export const containerStyles = {
    width: "100%",
    height: "100%",
    fontFamily: '"Tactic Sans", sans-serif',
};

/** Estilos del wrapper - extendido de TableGeneralStyles */
export const wrapperStyles = {
    ...TableGeneralStyles,
    width: { xs: "280px", sm: "520px", md: "920px", lg: "920px", xl: "1220px" },
    top: { xs: "10px", sm: "1%", md: "5%", lg: "5%", xl: "8%" },
};

// =============================================================================
// ESTILOS DEL TÍTULO (Neo-Brutalista con stroke + shadow)
// =============================================================================

/** Título con efecto de outline negro y sombra */
export const titleStyles = {
    ...TableTitleStyles,
    color: COLORS.white,
    textShadow: `
        -1px -1px 0 ${COLORS.black},
        1px -1px 0 ${COLORS.black},
        -1px 1px 0 ${COLORS.black},
        1px 1px 0 ${COLORS.black},
        3px 3px 0 ${COLORS.black}
    `,
    letterSpacing: "2px",
    marginBottom: "16px",
};

// =============================================================================
// ESTILOS DE ALERTAS NEO-BRUTALISTAS
// Fondo oscuro #2B2E34 con texto blanco
// =============================================================================

const alertBaseStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    border: `1px solid #1A1C20`,      // Borde oscuro sutil
    borderRadius: "8px",
    boxShadow: "0px 2px 4px rgba(0,0,0,0.3)",  // Sombra sutil
    marginBottom: "12px",
    backgroundColor: COLORS.grayDark,  // Fondo oscuro
    color: COLORS.white,               // Texto blanco
    "& .MuiAlert-message": {
        fontFamily: '"Tactic Sans", sans-serif',
        fontWeight: 400,
        color: COLORS.white,
    },
    "& .MuiAlert-icon": {
        alignItems: "center",
        color: COLORS.white,
    },
};

export const alertErrorStyles = {
    ...alertBaseStyles,
    "& .MuiAlert-icon": {
        color: COLORS.error,
    },
};

export const alertWarningStyles = {
    ...alertBaseStyles,
    "& .MuiAlert-icon": {
        color: COLORS.warning,
    },
};

export const alertSuccessStyles = {
    ...alertBaseStyles,
    "& .MuiAlert-icon": {
        color: COLORS.success,
    },
};

// =============================================================================
// ESTILOS DEL CONTENEDOR DE LA GRILLA
// Altura dinámica basada en contenido, fondo oscuro
// =============================================================================

export const gridContainerStyles = {
    // Height dinámico - crece con el contenido
    height: "auto",
    minHeight: "200px",
    maxHeight: "calc(100vh - 320px)",  // Máximo para no desbordar
    border: `1px solid #1A1C20`,       // Borde oscuro sutil
    borderRadius: "8px",
    overflow: "hidden",
    // Paper shadow effect
    boxShadow: "0px 3px 1px -2px rgba(0,0,0,0.2), 0px 2px 2px 0px rgba(0,0,0,0.14), 0px 1px 5px 0px rgba(0,0,0,0.12)",
    // Fondo oscuro para la tabla
    backgroundColor: COLORS.grayDark,
};

// =============================================================================
// ESTILOS DE LA LEYENDA
// Fondo oscuro #2B2E34 con texto blanco
// =============================================================================

export const legendStyles = {
    marginTop: "16px",
    padding: "16px 20px",
    backgroundColor: COLORS.grayDark,    // Fondo oscuro
    borderRadius: "8px",
    border: `1px solid #1A1C20`,         // Borde oscuro sutil
    boxShadow: "0px 2px 4px rgba(0,0,0,0.3)",
};

export const legendTitleStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 700,
    fontSize: "16px",
    marginBottom: "12px",
    color: COLORS.white,                  // Texto blanco
};

export const legendTextStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 400,
    fontSize: "14px",
    color: COLORS.white,                  // Texto blanco
    lineHeight: 1.8,
};

/** Estilos para teclas (kbd) en la leyenda - Fondo oscuro con borde gris */
export const kbdStyles: React.CSSProperties = {
    padding: "3px 8px",
    backgroundColor: "#1A1C20",
    border: `1px solid #555`,
    borderRadius: "4px",
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 500,
    fontSize: "12px",
    boxShadow: "1px 1px 0 #000",
    display: "inline-block",
    marginLeft: "4px",
    marginRight: "4px",
    color: COLORS.white,
};

/** Estilos para badges de estado en la leyenda - Bordes blancos para contraste */
export const getStatusBadgeStyles = (bgColor: string, textColor: string): React.CSSProperties => ({
    display: "inline-block",
    padding: "2px 8px",
    backgroundColor: bgColor,
    color: textColor,
    border: `2px solid #444`,  // Borde gris claro para contraste
    borderRadius: "4px",
    marginRight: "8px",
    fontWeight: 600,
});

// =============================================================================
// TEMA PERSONALIZADO NEO-BRUTALISTA PARA GLIDE DATA GRID
// Tabla completamente oscura con texto blanco (como en la imagen de referencia)
// Fuente pequeña Tactic Sans
// =============================================================================

export const gridTheme: Partial<Theme> = {
    // Colores de acento
    accentColor: COLORS.primary,
    accentLight: "#4D94FF",
    
    // Colores de texto - BLANCO para contrastar con fondo oscuro
    textDark: COLORS.white,           // Texto principal blanco
    textMedium: "#CCCCCC",            // Texto secundario gris claro
    textLight: "#999999",             // Texto terciario
    textBubble: COLORS.white,
    
    // Iconos de header - BLANCOS (hover azul se maneja en CSS)
    bgIconHeader: COLORS.grayDark,    // Fondo igual al header para que no destaque
    fgIconHeader: COLORS.white,       // Icono blanco
    
    // Headers - Texto BLANCO sobre fondo OSCURO
    textHeader: COLORS.white,
    textHeaderSelected: COLORS.primary,
    textGroupHeader: COLORS.white,        // Texto de grupos de columnas blanco
    
    // Celdas - Fondo OSCURO con filas alternadas
    bgCell: COLORS.grayDark,          // Fila par: #2B2E34
    bgCellMedium: "#1E2127",          // Fila impar: más oscuro
    
    // Headers - Fondo OSCURO #2B2E34
    bgHeader: COLORS.grayDark,
    bgHeaderHasFocus: "#3a3d44",
    bgHeaderHovered: "#3a3d44",
    
    // Burbujas y selección
    bgBubble: COLORS.grayMedium,
    bgBubbleSelected: COLORS.primary,
    bgSearchResult: "#4D94FF33",      // Azul semi-transparente
    
    // Bordes - Gris visible para separación clara
    borderColor: "#3a3d44",           // Borde gris oscuro visible
    horizontalBorderColor: "#3a3d44", // Líneas horizontales
    drilldownBorder: COLORS.primary,
    
    // Links - Azul para contraste
    linkColor: COLORS.primary,
    
    // Tipografía Tactic Sans - PEQUEÑA (11px contenido, 12px headers)
    headerFontStyle: "600 12px",
    baseFontStyle: "500 11px",
    fontFamily: '"Tactic Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
};

// =============================================================================
// CONFIGURACIÓN DE DIMENSIONES DE LA GRILLA
// =============================================================================

export const GRID_DIMENSIONS = {
    rowHeight: 36,           // Filas más compactas
    headerHeight: 40,        // Headers compactos
    groupHeaderHeight: 34,   // Grupo headers compactos
};
