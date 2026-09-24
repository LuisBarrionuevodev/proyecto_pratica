/**
 * Design tokens — shell layout, motion y paleta glass (DIGITALIZA).
 * Fuente única para theme MUI y estilos glass; no importar desde GlassStyles aquí.
 */

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

/** Paleta glass / superficies (equivalente histórico a GLASS_COLORS) */
export const color = {
  sidebarBg: "rgba(18, 18, 22, 0.94)",
  contentBg: "rgba(18, 18, 22, 0.94)",
  cardBg: "rgba(30, 32, 38, 0.85)",
  hoverBg: "rgba(255, 255, 255, 0.06)",
  activeBg: "rgba(255, 255, 255, 0.10)",
  borderLight: "rgba(255, 255, 255, 0.06)",
  borderMedium: "rgba(255, 255, 255, 0.10)",
  borderActive: "rgba(1, 102, 255, 0.5)",
  textPrimary: "#FFFFFF",
  textSecondary: "rgba(255, 255, 255, 0.7)",
  textMuted: "rgba(255, 255, 255, 0.45)",
  primary: "#0166FF",
  primaryGlow: "rgba(1, 102, 255, 0.3)",
} as const;
