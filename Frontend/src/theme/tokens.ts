/**
 * Design tokens — shell layout, motion y paleta glass (DIGITALIZA).
 * Fuente única para theme MUI y estilos glass; no importar desde GlassStyles aquí.
 */
import { legacyGlassColorMap } from "./colors/legacyGlass";

export const layoutShell = {
  /** Altura fija del header (TopBar) */
  topBarHeightPx: 56,
  /** Ancho del drawer lateral expandido */
  sidebarExpandedPx: 250,
  /** Ancho del drawer lateral colapsado (solo iconos) */
  sidebarCollapsedPx: 72,
} as const;

/** Transición sincronizada (sidebar ↔ content) */
export const motion = {
  durationMs: 200,
  easing: "ease-out" as const,
  css: "all 0.2s ease-out",
} as const;

/** Paleta glass — alias de `darkColors` (claves históricas). Preferir `semanticColors` en código nuevo. */
export const color = { ...legacyGlassColorMap };
