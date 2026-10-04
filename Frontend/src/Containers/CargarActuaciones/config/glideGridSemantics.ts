import type { SemanticColors } from "../../../theme/colors";

const GLIDE_PAINTED_CELL_FONT = "700 13px";

/** Override de header de grupo/columna Glide (colores concretos; no CSS vars). */
export function glideColumnHeaderThemeOverride(colors: SemanticColors) {
  return {
    bgHeader: colors.surface.tableHeader,
    bgHeaderHovered: colors.surface.tableRowHover,
    textHeader: colors.text.primary,
    fgIconHeader: colors.text.primary,
    bgIconHeader: "transparent",
  };
}

export function glideGroupHeaderThemeOverride(colors: SemanticColors) {
  return {
    bgHeader: colors.surface.tableHeader,
    textGroupHeader: colors.text.primary,
    fgIconHeader: colors.text.primary,
  };
}

export type GlideCellVisualState =
  | "empty"
  | "error"
  | "ok"
  | "pending"
  | "validating"
  | "readonly";

/**
 * Fondos/texto de celda Glide según estado (dark y light).
 */
/**
 * Tema de celda para dropdowns Glide: fuerza texto de catálogo legible (dark/light).
 */
export function resolveGlideDropdownCellTheme(
  colors: SemanticColors,
  state: GlideCellVisualState
): { bgCell: string; textDark: string; textMedium: string; textBubble: string; baseFontStyle?: string } {
  const base = resolveGlideCellTheme(colors, state);
  return {
    ...base,
    textMedium: colors.text.primary,
    textBubble: colors.text.primary,
  };
}

export function resolveGlideCellTheme(
  colors: SemanticColors,
  state: GlideCellVisualState
): { bgCell: string; textDark: string; baseFontStyle?: string } {
  switch (state) {
    case "empty":
      return { bgCell: colors.surface.tableRowEven, textDark: colors.text.primary };
    case "error":
      return {
        bgCell: colors.status.errorSurface,
        textDark: colors.text.primary,
        baseFontStyle: GLIDE_PAINTED_CELL_FONT,
      };
    case "ok":
      return {
        bgCell: colors.status.successSurface,
        textDark: colors.text.primary,
        baseFontStyle: GLIDE_PAINTED_CELL_FONT,
      };
    case "pending":
      return {
        bgCell: colors.status.warningSurface,
        textDark: colors.text.primary,
        baseFontStyle: GLIDE_PAINTED_CELL_FONT,
      };
    case "validating":
      return { bgCell: colors.surface.panelSubtle, textDark: colors.text.secondary };
    case "readonly":
      return { bgCell: colors.surface.panelSubtle, textDark: colors.text.muted };
    default:
      return { bgCell: colors.surface.tableRowEven, textDark: colors.text.primary };
  }
}
