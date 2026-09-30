/**
 * Tema Neo-Brutalista para Glide Data Grid
 */
import type { Theme } from "@glideapps/glide-data-grid";
import { COLORS } from "../styles/cargarActuacionesStyles";
import { darkColors } from "../../../theme/colors";
import { FONT_FAMILY_UI } from "../../../theme/typography";

const c = darkColors;

// =============================================================================
// TEMA DE LA GRILLA
// =============================================================================
export const gridTheme: Partial<Theme> = {
    // Colores de acento
    accentColor: COLORS.primary,
    accentLight: "#4D94FF",
    
    // Colores de texto
    textDark: COLORS.white,
    textMedium: "rgba(255, 255, 255, 0.8)",
    textLight: "rgba(255, 255, 255, 0.6)",
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
    bgHeaderHasFocus: c.border.strong,
    bgHeaderHovered: c.border.strong,
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
    fontFamily: FONT_FAMILY_UI,
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
