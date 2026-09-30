/**
 * Tema Neo-Brutalista para Glide Data Grid
 */
import type { Theme } from "@glideapps/glide-data-grid";
import type { SemanticColors } from "../../../theme/colors";
import { darkColors } from "../../../theme/colors";
import { FONT_FAMILY_UI } from "../../../theme/typography";

/**
 * Tema Glide con colores concretos (canvas no resuelve CSS variables).
 */
export function createGridTheme(colors: SemanticColors): Partial<Theme> {
  const c = colors;
  return {
    accentColor: c.action.primary,
    accentLight: "#4D94FF",

    textDark: c.text.primary,
    textMedium: c.text.secondary,
    textLight: c.text.muted,
    textBubble: c.text.primary,
    textHeader: c.text.primary,
    textGroupHeader: c.text.primary,
    textHeaderSelected: c.action.primary,

    bgIconHeader: "transparent",
    fgIconHeader: c.text.primary,

    bgCell: c.surface.tableRowEven,
    bgCellMedium: c.surface.tableRowOdd,
    bgHeader: c.surface.panelElevated,
    bgHeaderHasFocus: c.surface.tableRowHover,
    bgHeaderHovered: c.surface.tableRowHover,
    bgBubble: c.surface.tableRowEven,
    bgBubbleSelected: c.action.primary,
    bgSearchResult: c.status.warningSurface,

    borderColor: c.border.strong,
    horizontalBorderColor: c.border.strong,
    drilldownBorder: c.action.primary,

    linkColor: c.action.primary,

    headerFontStyle: "600 12px",
    baseFontStyle: "11px",
    fontFamily: FONT_FAMILY_UI,
  };
}

/** @deprecated Usar `createGridTheme(colors)` con `useDigitalizaTheme()`. */
export const gridTheme: Partial<Theme> = createGridTheme(darkColors);

// =============================================================================
// DIMENSIONES DE LA GRILLA
// =============================================================================
export const GRID_DIMENSIONS = {
  rowHeight: 36,
  headerHeight: 42,
  groupHeaderHeight: 36,
  trailingRowHeight: 36,
  minHeight: 400,
  maxHeightOffset: 280,
};

/**
 * Calcula la altura dinámica de la tabla según el número de filas
 */
export const calculateTableHeight = (rowCount: number): number => {
  const { rowHeight, headerHeight, groupHeaderHeight, trailingRowHeight, minHeight, maxHeightOffset } =
    GRID_DIMENSIONS;

  const contentHeight = groupHeaderHeight + headerHeight + rowCount * rowHeight + trailingRowHeight;
  const maxHeight = window.innerHeight - maxHeightOffset;

  return Math.min(Math.max(contentHeight, minHeight), maxHeight);
};
