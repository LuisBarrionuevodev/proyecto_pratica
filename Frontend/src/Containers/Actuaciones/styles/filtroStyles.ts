import type { SxProps, Theme } from "@mui/material";
import { FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING } from "../../../styles/functionalPageShell";
import { GLASS_COLORS, moduleFiltersSurfaceSx } from "../../../styles/GlassStyles";

// =============================================================================
// ESTILOS GLASSMORPHISM PARA FILTROS DE ACTUACIONES
// =============================================================================

export const COLORS = {
    primary: "#0166FF",
    black: "#000000",
    white: "#FFFFFF",
    grayDark: "#2B2E34",
    grayMedium: "#353535",
    rowOdd: "#1E2127",
    border: "#3a3d44",
    success: "#2D9F4B",
    error: "#E53935",
};

// =============================================================================
// LAYOUT PRINCIPAL - Aprovecha todo el espacio del ContentShell
// =============================================================================

export const wrapperStyles: SxProps<Theme> = {
  width: "100%",
  height: "100%",
  display: "flex",
  flexDirection: "column",
  boxSizing: "border-box",
  padding: { xs: 2, sm: 3 },
};

/** Shell de sección con tabs (Relevamientos): un solo padding, sin height 100% para no colapsar hijos al cambiar pestaña. */
export const relevamientosSectionOuterSx: SxProps<Theme> = {
  width: "100%",
  display: "flex",
  flexDirection: "column",
  gap: FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING,
  boxSizing: "border-box",
  padding: { xs: 2, sm: 3 },
  minHeight: 0,
};

/** Columna de contenido bajo tabs: sin padding extra ni height 100% (el padre ya define el área). */
export const moduleContentColumnSx: SxProps<Theme> = {
  width: "100%",
  display: "flex",
  flexDirection: "column",
  minHeight: 0,
  boxSizing: "border-box",
  gap: FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING,
};

// Título oculto (ahora en el breadcrumb del AppLayout)
export const titleStyles: SxProps<Theme> = {
    display: "none",
};

// =============================================================================
// CONTENEDOR DE FILTROS — superficie F3.8c (`moduleFiltersSurfaceSx`), coherente con slices/tabs de Actas.
// =============================================================================

/** Superficie base de subpaneles (filtros, bloques meta). */
export const filterPanelSurfaceSx: SxProps<Theme> = {
  ...moduleFiltersSurfaceSx,
};

export const filtroContainerStyles: SxProps<Theme> = {
  ...filterPanelSurfaceSx,
  mb: FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING,
  p: 2,
  /** En `wrapperStyles` (flex column + height 100%) evita que el panel de filtros se aplaste. */
  flexShrink: 0,
};

export const filtroTitleStyles: SxProps<Theme> = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontWeight: 700,
  fontSize: "18px",
  color: COLORS.white,
  mb: 2,
};

export const filtroSectionTitleStyles: SxProps<Theme> = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontWeight: 600,
  fontSize: "15px",
  color: COLORS.white,
  mb: 0.75,
};

export const filtroHintStyles: SxProps<Theme> = {
  color: "rgba(255,255,255,0.75)",
  fontSize: "0.85rem",
  mb: 1.5,
  lineHeight: 1.45,
};

export const filtroGridStyles: SxProps<Theme> = {
  display: "grid",
  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" },
  gap: 2,
  mb: 2,
};

export const filtroItemStyles: SxProps<Theme> = {
  "& .MuiInputLabel-root": {
    color: COLORS.white,
    fontFamily: '"Tactic Sans", sans-serif',
    "&.Mui-focused": { color: COLORS.primary },
  },
  "& .MuiInputBase-root": {
    backgroundColor: COLORS.rowOdd,
    color: COLORS.white,
    fontFamily: '"Tactic Sans", sans-serif',
    borderRadius: 3,
    "& input": {
      color: COLORS.white,
      "&::placeholder": { color: GLASS_COLORS.textMuted, opacity: 1 },
    },
    "& .MuiSvgIcon-root": { color: COLORS.white },
    "&:hover": {
      backgroundColor: COLORS.grayMedium,
      "& .MuiOutlinedInput-notchedOutline": {
        borderColor: GLASS_COLORS.borderMedium,
      },
    },
    "&.Mui-focused": {
      backgroundColor: COLORS.grayMedium,
      "& .MuiOutlinedInput-notchedOutline": {
        borderColor: COLORS.primary,
      },
    },
  },
  "& .MuiOutlinedInput-notchedOutline": {
    borderColor: GLASS_COLORS.borderLight,
  },
  "& .MuiMenuItem-root": {
    backgroundColor: COLORS.rowOdd,
    color: COLORS.white,
    "&:hover": {
      backgroundColor: COLORS.grayMedium,
    },
    "&.Mui-selected": {
      backgroundColor: COLORS.grayMedium,
    },
  },
};

export const filtroButtonsStyles: SxProps<Theme> = {
  display: "flex",
  gap: 1.5,
  justifyContent: "flex-end",
  alignItems: "center",
  flexWrap: "wrap",
};

/** Alias canónicos STAB-10 — mismo sistema en todos los filtros. */
export const filterActionsSx = filtroButtonsStyles;

export const filtroButtonPrimaryStyles: SxProps<Theme> = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontWeight: 600,
  fontSize: "14px",
  backgroundColor: COLORS.primary,
  color: COLORS.white,
  textTransform: "none",
  padding: "10px 24px",
  borderRadius: "6px",
  border: `1px solid ${GLASS_COLORS.borderActive}`,
  boxShadow: "0px 2px 4px rgba(0,0,0,0.3)",
  "&:hover": {
    backgroundColor: "#0152CC",
    boxShadow: "0px 4px 8px rgba(0,0,0,0.4)",
  },
};

export const filtroButtonSecondaryStyles: SxProps<Theme> = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontWeight: 600,
  fontSize: "14px",
  backgroundColor: "transparent",
  color: COLORS.white,
  textTransform: "none",
  padding: "10px 24px",
  borderRadius: "6px",
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
  "&:hover": {
    backgroundColor: COLORS.rowOdd,
    borderColor: GLASS_COLORS.borderLight,
  },
};

export const filterPrimaryButtonSx = filtroButtonPrimaryStyles;
export const filterSecondaryButtonSx = filtroButtonSecondaryStyles;

/** Fila de acciones en filtros compactos (urgentes, panel contexto). */
export const filterCompactActionsSx: SxProps<Theme> = {
  display: "flex",
  gap: 1,
  alignItems: "center",
  flexWrap: "wrap",
};

/** Botón primary compacto alineado a inputs `size="small"`. */
export const filterCompactPrimaryButtonSx: SxProps<Theme> = {
  ...filtroButtonPrimaryStyles,
  fontSize: "13px",
  padding: "7px 16px",
  minHeight: 36,
  flexShrink: 0,
};

export const filterCompactSecondaryButtonSx: SxProps<Theme> = {
  ...filtroButtonSecondaryStyles,
  fontSize: "13px",
  padding: "7px 16px",
  minHeight: 36,
  flexShrink: 0,
};

// =============================================================================
// METADATA E INFO - Sin blur para rendimiento
// =============================================================================

export const metaInfoStyles: SxProps<Theme> = {
  ...filterPanelSurfaceSx,
  mb: 2,
  p: 2,
  display: "flex",
  alignItems: "center",
  gap: 2,
  flexWrap: "wrap",
  flexShrink: 0,
};

export const metaItemStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: "13px",
    color: GLASS_COLORS.textSecondary,
    "& strong": {
        color: COLORS.primary,
        fontWeight: 600,
    },
};

// =============================================================================
// ALERTS Y ERRORES
// =============================================================================

/** Estilo canónico para alertas en fondos dark institucionales (borde alineado a tokens glass). */
export const alertBaseStyles: SxProps<Theme> = {
  fontFamily: '"Tactic Sans", sans-serif',
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
  borderRadius: "12px",
  mb: 2,
  backgroundColor: GLASS_COLORS.cardBg,
  color: COLORS.white,
  "& .MuiAlert-icon": { color: COLORS.white },
  "& .MuiAlert-message": { fontFamily: '"Tactic Sans", sans-serif' },
};

export const errorAlertStyles: SxProps<Theme> = {
  mb: 2,
  backgroundColor: "rgba(92, 35, 35, 0.9)",
  color: COLORS.white,
  border: `1px solid ${COLORS.error}`,
  borderRadius: "12px",
  "& .MuiAlert-icon": {
    color: COLORS.error,
  },
  "& .MuiAlert-message": {
    fontFamily: '"Tactic Sans", sans-serif',
  },
};
