import { CSS_VAR_NAMES as V } from "../applyCssVariables";

/**
 * Claves históricas de `GLASS_COLORS` → referencias CSS dinámicas (FRONT-PROD.3).
 * Los valores concretos se inyectan con `applyDigitalizaCssVariables(colors)`.
 */
export const legacyGlassColorMap = {
  sidebarBg: `var(${V.surfaceSidebar})`,
  contentBg: `var(${V.surfaceContent})`,
  cardBg: `var(${V.surfacePanel})`,
  hoverBg: `var(${V.actionHover})`,
  activeBg: `var(${V.actionSelected})`,
  borderLight: `var(${V.borderSubtle})`,
  borderMedium: `var(${V.borderDefault})`,
  borderActive: `var(${V.borderActive})`,
  textPrimary: `var(${V.textPrimary})`,
  textSecondary: `var(${V.textSecondary})`,
  textMuted: `var(${V.textMuted})`,
  primary: `var(${V.actionPrimary})`,
  primaryGlow: `var(${V.actionPrimaryGlow})`,
} as const;

export type LegacyGlassColorKey = keyof typeof legacyGlassColorMap;
