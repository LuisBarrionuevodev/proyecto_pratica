import { darkColors } from "./dark";

/**
 * Mapa retrocompatible con claves históricas de `GLASS_COLORS` / `token.color`.
 * Una sola fuente de verdad: `darkColors`.
 */
export const legacyGlassColorMap = {
  sidebarBg: darkColors.surface.sidebar,
  contentBg: darkColors.surface.content,
  cardBg: darkColors.surface.panel,
  hoverBg: darkColors.action.hover,
  activeBg: darkColors.action.selected,
  borderLight: darkColors.border.subtle,
  borderMedium: darkColors.border.default,
  borderActive: darkColors.border.active,
  textPrimary: darkColors.text.primary,
  textSecondary: darkColors.text.secondary,
  textMuted: darkColors.text.muted,
  primary: darkColors.action.primary,
  primaryGlow: darkColors.action.primaryGlow,
} as const;

export type LegacyGlassColorKey = keyof typeof legacyGlassColorMap;
