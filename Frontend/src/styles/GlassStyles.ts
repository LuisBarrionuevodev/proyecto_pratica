import type { SxProps, Theme } from "@mui/material";

import { color as tokenColor, motion } from "../theme/tokens";

// =============================================================================
// ESTILOS GLASSMORPHISM REUTILIZABLES (optimizado para rendimiento)
// =============================================================================

// Constantes de transición sincronizadas (sidebar <-> content) — desde tokens
export const TRANSITION = {
    duration: motion.durationMs,
    easing: motion.easing,
    css: motion.css,
};

// Paleta de colores glass — valores desde tokens (misma forma pública)
export const GLASS_COLORS = { ...tokenColor };

// Estilo glass base para sidebar
export const glassSidebar: SxProps<Theme> = {
    backgroundColor: GLASS_COLORS.sidebarBg,
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    border: `1px solid ${GLASS_COLORS.borderLight}`,
    boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
};

// Estilo glass base para content shell
export const glassContent: SxProps<Theme> = {
    backgroundColor: GLASS_COLORS.contentBg,
    backdropFilter: "blur(16px)",
    WebkitBackdropFilter: "blur(16px)",
    border: `1px solid ${GLASS_COLORS.borderLight}`,
    boxShadow: "0 10px 40px rgba(0, 0, 0, 0.5)",
};

// Estilo glass para cards/boxes auxiliares
export const glassCard: SxProps<Theme> = {
    backgroundColor: GLASS_COLORS.cardBg,
    backdropFilter: "blur(14px)",
    WebkitBackdropFilter: "blur(14px)",
    border: `1px solid ${GLASS_COLORS.borderMedium}`,
    boxShadow: "0 4px 24px rgba(0, 0, 0, 0.3)",
    borderRadius: "16px",
};

/**
 * Panel glass tipo Paper para cabecera con tabs (Mapa, Rutas, Cargar actuación, Relevamientos, etc.).
 */
export const glassTabsHeaderPanelSx: SxProps<Theme> = {
    ...glassCard,
    p: 2,
    overflow: "hidden",
};

// Estilo para item de menú activo
export const glassActiveItem: SxProps<Theme> = {
    backgroundColor: GLASS_COLORS.activeBg,
    borderLeft: `3px solid ${GLASS_COLORS.primary}`,
    boxShadow: `inset 0 0 20px ${GLASS_COLORS.primaryGlow}`,
};

// Estilo para item de menú hover
export const glassHoverItem: SxProps<Theme> = {
    backgroundColor: GLASS_COLORS.hoverBg,
};

// Divider sutil glass
export const glassDivider: SxProps<Theme> = {
    borderColor: GLASS_COLORS.borderLight,
    opacity: 0.6,
};

// Header de sección en sidebar
export const glassSectionHeader: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: "10px",
    fontWeight: 600,
    letterSpacing: "1.5px",
    textTransform: "uppercase",
    color: GLASS_COLORS.textMuted,
    paddingX: 2,
    paddingY: 1,
    marginTop: 1.5,
};

// Header de contenido (breadcrumb "> Vista")
export const glassContentHeader: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: "13px",
    fontWeight: 500,
    color: GLASS_COLORS.textSecondary,
    display: "flex",
    alignItems: "center",
    gap: 0.5,
    paddingX: 3,
    paddingY: 2,
    borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
};
