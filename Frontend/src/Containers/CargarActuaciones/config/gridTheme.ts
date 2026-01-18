/**
 * Tema Neo-Brutalista para Glide Data Grid
 */
import type { Theme } from "@glideapps/glide-data-grid";
import { COLORS } from "../styles/cargarActuacionesStyles";

// =============================================================================
// TEMA DE LA GRILLA
// =============================================================================
export const gridTheme: Partial<Theme> = {
    // Colores de acento
    accentColor: COLORS.primary,
    accentLight: "#4D94FF",
    
    // Colores de texto
    textDark: COLORS.white,
    textMedium: "#CCCCCC",
    textLight: "#999999",
    textBubble: COLORS.white,
    textHeader: COLORS.white,
    textGroupHeader: COLORS.white,
    textHeaderSelected: COLORS.primary,
    
    // Colores de iconos - todos blancos
    bgIconHeader: "transparent",
    fgIconHeader: COLORS.white,
    
    // Colores de fondo
    bgCell: COLORS.grayDark,
    bgCellMedium: COLORS.rowOdd,
    bgHeader: COLORS.grayDark,
    bgHeaderHasFocus: "#3a3d44",
    bgHeaderHovered: "#3a3d44",
    bgBubble: COLORS.grayDark,
    bgBubbleSelected: COLORS.primary,
    bgSearchResult: COLORS.warningLight,
    
    // Bordes
    borderColor: COLORS.border,
    horizontalBorderColor: COLORS.border,
    drilldownBorder: COLORS.primary,
    
    // Links
    linkColor: COLORS.primary,
    
    // Fuentes
    headerFontStyle: "600 12px",
    baseFontStyle: "11px",
    fontFamily: '"Tactic Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
};

// =============================================================================
// DIMENSIONES DE LA GRILLA
// =============================================================================
export const GRID_DIMENSIONS = {
    rowHeight: 36,
    headerHeight: 42,
    groupHeaderHeight: 36,
    trailingRowHeight: 36,
    minHeight: 400,
    maxHeightOffset: 280, // Para calcular maxHeight = window.innerHeight - offset
};

/**
 * Calcula la altura dinámica de la tabla según el número de filas
 */
export const calculateTableHeight = (rowCount: number): number => {
    const { rowHeight, headerHeight, groupHeaderHeight, trailingRowHeight, minHeight, maxHeightOffset } = GRID_DIMENSIONS;
    
    const contentHeight = groupHeaderHeight + headerHeight + (rowCount * rowHeight) + trailingRowHeight;
    const maxHeight = window.innerHeight - maxHeightOffset;
    
    return Math.min(Math.max(contentHeight, minHeight), maxHeight);
};
