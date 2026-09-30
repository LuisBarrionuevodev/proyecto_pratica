import type { SemanticColors } from "../../../theme/colors";
import { lightColors } from "../../../theme/colors";

const GLIDE_PAINTED_CELL_FONT = "600 12px";

function isLightPalette(colors: SemanticColors): boolean {
  return colors.surface.app === lightColors.surface.app;
}

/** Texto de celdas con fondo de estado (error/ok/pendiente): alto contraste por tema. */
function paintedCellText(colors: SemanticColors): string {
  return isLightPalette(colors) ? colors.text.primary : colors.text.inverse;
}

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
        textDark: paintedCellText(colors),
        baseFontStyle: GLIDE_PAINTED_CELL_FONT,
      };
    case "ok":
      return {
        bgCell: colors.status.successSurface,
        textDark: paintedCellText(colors),
        baseFontStyle: GLIDE_PAINTED_CELL_FONT,
      };
    case "pending":
      return {
        bgCell: colors.status.warningSurface,
        textDark: paintedCellText(colors),
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
