/**
 * Tokens de color semánticos (FRONT-PROD.2/3).
 */
import { darkColors } from "./dark";
import { lightColors } from "./light";

export { darkColors } from "./dark";
export { lightColors } from "./light";
export type { SemanticColors } from "./semanticColorsType";
export { legacyGlassColorMap } from "./legacyGlass";

export type DigitalizaThemeMode = "dark" | "light";

/**
 * Resuelve la paleta semántica para el modo dado (sin mutación global).
 */
export function getSemanticColors(mode: DigitalizaThemeMode) {
  return mode === "light" ? lightColors : darkColors;
}

/**
 * @deprecated Representa solo dark legacy; usar `getSemanticColors(mode)` o `useDigitalizaTheme().colors`.
 */
export const semanticColors = darkColors;
