/**
 * Tokens de color semánticos (FRONT-PROD.2).
 * Hoy solo dark en uso; light se agregará en FRONT-PROD.3.
 */
import { darkColors } from "./dark";

export { darkColors } from "./dark";
export type { DarkSemanticColors } from "./dark";
export { legacyGlassColorMap } from "./legacyGlass";

/** Paleta activa de la aplicación (modo oscuro hasta FRONT-PROD.3). */
export const semanticColors = darkColors;
