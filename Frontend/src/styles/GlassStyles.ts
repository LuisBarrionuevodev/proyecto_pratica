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

/**
 * Tabs secundarios (p. ej. Pendientes | Realizados bajo filtros): más liviano que la cabecera principal,
 * alineado visualmente con sub-secciones dentro de una misma vista.
 */
export const glassTabsSecondaryPanelSx: SxProps<Theme> = {
    backgroundColor: "rgba(255, 255, 255, 0.035)",
    backdropFilter: "blur(10px)",
    WebkitBackdropFilter: "blur(10px)",
    border: `1px solid ${GLASS_COLORS.borderLight}`,
    borderRadius: "12px",
    boxShadow: "none",
    p: 1.25,
    overflow: "hidden",
};

/**
 * Misma superficie que `glassTabsSecondaryPanelSx` pero con altura mínima estable para barras de tabs/chips
 * (evita que la caja “encoja” al cambiar selección o variante de chip).
 */
export const glassTabsSecondaryPanelBarSx: SxProps<Theme> = {
    ...glassTabsSecondaryPanelSx,
    minHeight: 72,
    boxSizing: "border-box",
    display: "flex",
    alignItems: "center",
};

/** Fondo activo tab — más liviano que chip (`rgba(1,102,255,0.28)`) por coexistencia con indicador. */
const GLASS_TAB_SELECTED_BG = "rgba(1, 102, 255, 0.12)";
const GLASS_TAB_SELECTED_BG_HOVER = "rgba(1, 102, 255, 0.2)";

/**
 * MUI `Tabs` dentro de `glassTabsSecondaryPanelSx`: tipografía y colores alineados a Relevamientos (blueprint tabs secundarios).
 */
export const glassSecondaryTabsSx: SxProps<Theme> = {
    width: "100%",
    flex: 1,
    alignSelf: "stretch",
    marginBottom: 0,
    minHeight: 48,
    fontFamily: '"Tactic Sans", sans-serif',
    "& .MuiTab-root": {
        color: GLASS_COLORS.textSecondary,
        textTransform: "none",
        minHeight: 48,
        fontWeight: 500,
        fontSize: "0.9375rem",
        borderRadius: "10px",
        transition: `color ${TRANSITION.duration}ms ${TRANSITION.easing}, background-color ${TRANSITION.duration}ms ${TRANSITION.easing}`,
        "&:hover": {
            color: GLASS_COLORS.textPrimary,
        },
        "&:not(.Mui-selected):hover": {
            backgroundColor: GLASS_COLORS.hoverBg,
        },
    },
    "& .MuiTab-root.Mui-selected": {
        color: GLASS_COLORS.textPrimary,
        backgroundColor: GLASS_TAB_SELECTED_BG,
    },
    "& .MuiTab-root.Mui-selected:hover": {
        backgroundColor: GLASS_TAB_SELECTED_BG_HOVER,
    },
    "& .MuiTabs-indicator": {
        backgroundColor: GLASS_COLORS.primary,
    },
};

// -----------------------------------------------------------------------------
// F3.8c — Chrome común de módulos (slices/tabs + filtros). Benchmark: Actas de comprobación.
// -----------------------------------------------------------------------------

/** `Paper` para filas de slices/tabs (full width del área de contenido). */
export const moduleSlicesPanelPaperSx: SxProps<Theme> = {
    ...glassTabsSecondaryPanelBarSx,
    width: "100%",
    maxWidth: "100%",
    boxSizing: "border-box",
};

/** `Tabs` MUI dentro de `moduleSlicesPanelPaperSx` (activo/inactivo unificado). */
export const moduleSlicesTabsSx: SxProps<Theme> = glassSecondaryTabsSx;

/** Superficie para paneles de filtros y bloques meta (sin altura mínima de barra de tabs). */
export const moduleFiltersSurfaceSx: SxProps<Theme> = {
    ...glassTabsSecondaryPanelSx,
    width: "100%",
    maxWidth: "100%",
    boxSizing: "border-box",
    /** No heredar `overflow: hidden` de tabs: recorta grillas de filtros en vistas flex (p. ej. Actuaciones). */
    overflow: "visible",
};

/** Cajas de resumen/contenido principal bajo slices (p. ej. Completar trabajo). */
export const moduleContentPanelPaperSx: SxProps<Theme> = {
    ...glassTabsSecondaryPanelSx,
    width: "100%",
    maxWidth: "100%",
    boxSizing: "border-box",
    p: { xs: 2, sm: 2.5 },
    overflow: "visible",
};

/**
 * Tarjeta de entrada / CTA alineada al chrome F3.8c (misma superficie que slices/tabs, sin barra de pestañas).
 * Usar en `CardGlass` con `sx` para sobreescribir `glassCard`.
 */
export const moduleHeroCardSx: SxProps<Theme> = {
    backgroundColor: "rgba(255, 255, 255, 0.035)",
    backdropFilter: "blur(10px)",
    WebkitBackdropFilter: "blur(10px)",
    border: `1px solid ${GLASS_COLORS.borderLight}`,
    borderRadius: "12px",
    boxShadow: "none",
    overflow: "visible",
};

/** Tabs principales: superficie activa un poco más marcada que secundarios, aún por debajo del chip (~0.28). */
const GLASS_TAB_PRIMARY_SELECTED_BG = "rgba(1, 102, 255, 0.16)";
const GLASS_TAB_PRIMARY_SELECTED_BG_HOVER = "rgba(1, 102, 255, 0.24)";

/**
 * MUI `Tabs` en cabeceras principales (`glassTabsHeaderPanelSx`): misma familia que secundarios,
 * con más jerarquía (altura/tipografía/peso) e indicador explícito — no depender del default del tema.
 * Usar junto a `glassTabsHeaderPanelSx` (p. ej. Mapa modo tabs principales).
 */
export const glassPrimaryTabsSx: SxProps<Theme> = {
    width: "100%",
    marginBottom: 0,
    minHeight: 52,
    fontFamily: '"Tactic Sans", sans-serif',
    "& .MuiTab-root": {
        color: GLASS_COLORS.textSecondary,
        textTransform: "none",
        minHeight: 52,
        paddingTop: 1,
        paddingBottom: 1,
        fontWeight: 600,
        fontSize: "1rem",
        lineHeight: 1.35,
        borderRadius: "10px",
        transition: `color ${TRANSITION.duration}ms ${TRANSITION.easing}, background-color ${TRANSITION.duration}ms ${TRANSITION.easing}`,
        "&:hover": {
            color: GLASS_COLORS.textPrimary,
        },
        "&:not(.Mui-selected):hover": {
            backgroundColor: GLASS_COLORS.hoverBg,
        },
    },
    "& .MuiTab-root.Mui-selected": {
        color: GLASS_COLORS.textPrimary,
        fontWeight: 700,
        backgroundColor: GLASS_TAB_PRIMARY_SELECTED_BG,
    },
    "& .MuiTab-root.Mui-selected:hover": {
        backgroundColor: GLASS_TAB_PRIMARY_SELECTED_BG_HOVER,
    },
    "& .MuiTabs-indicator": {
        backgroundColor: GLASS_COLORS.primary,
        height: 3,
    },
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

/** Backdrop de diálogos: oscurece el shell y aplica blur ligero. */
export const glassDialogBackdropSx: SxProps<Theme> = {
    backgroundColor: "rgba(4, 6, 12, 0.72)",
    backdropFilter: "blur(8px)",
    WebkitBackdropFilter: "blur(8px)",
};

/** Paper del Dialog alineado al glass institucional. */
export const glassDialogPaperSx: SxProps<Theme> = {
    ...glassCard,
    backgroundColor: GLASS_COLORS.cardBg,
    color: GLASS_COLORS.textPrimary,
    maxHeight: "min(92vh, 920px)",
    display: "flex",
    flexDirection: "column",
};

export const glassDialogTitleSx: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: "15px",
    fontWeight: 700,
    letterSpacing: "0.06em",
    color: GLASS_COLORS.textPrimary,
    borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
    backgroundColor: "rgba(0, 0, 0, 0.22)",
    py: 1.5,
};

export const glassDialogContentSx: SxProps<Theme> = {
    backgroundColor: "rgba(14, 16, 22, 0.35)",
    color: GLASS_COLORS.textPrimary,
};

export const glassDialogActionsSx: SxProps<Theme> = {
    borderTop: `1px solid ${GLASS_COLORS.borderLight}`,
    backgroundColor: "rgba(0, 0, 0, 0.15)",
    color: GLASS_COLORS.textPrimary,
    px: 2,
    py: 1.5,
    gap: 1,
};
