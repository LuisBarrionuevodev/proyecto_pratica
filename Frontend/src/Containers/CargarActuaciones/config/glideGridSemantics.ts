import type { SemanticColors } from "../../../theme/colors";

/** Override de header de grupo/columna Glide (colores concretos; no CSS vars). */
export function glideColumnHeaderThemeOverride(colors: SemanticColors) {
  return {
    bgHeader: colors.surface.panelElevated,
    bgHeaderHovered: colors.surface.tableRowHover,
    textHeader: colors.text.primary,
    fgIconHeader: colors.text.primary,
    bgIconHeader: "transparent",
  };
}

export function glideGroupHeaderThemeOverride(colors: SemanticColors) {
  return {
    bgHeader: colors.surface.panelElevated,
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
): { bgCell: string; textDark: string } {
  switch (state) {
    case "empty":
      return { bgCell: colors.surface.tableRowEven, textDark: colors.text.primary };
    case "error":
      return { bgCell: colors.status.errorSurface, textDark: colors.status.error };
    case "ok":
      return { bgCell: colors.status.successSurface, textDark: colors.status.success };
    case "pending":
      return { bgCell: colors.status.warningSurface, textDark: colors.status.warning };
    case "validating":
      return { bgCell: colors.surface.panelSubtle, textDark: colors.text.secondary };
    case "readonly":
      return { bgCell: colors.surface.panelSubtle, textDark: colors.text.muted };
    default:
      return { bgCell: colors.surface.tableRowEven, textDark: colors.text.primary };
  }
}
