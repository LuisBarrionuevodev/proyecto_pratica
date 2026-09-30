import type { SxProps, Theme } from "@mui/material";
import { FUNCTIONAL_VIEW_TOP_TO_CONTENT_SPACING } from "../../../styles/functionalPageShell";
import { GLASS_COLORS, moduleFiltersSurfaceSx } from "../../../styles/GlassStyles";
import { CSS_VAR_NAMES as V } from "../../../theme/applyCssVariables";
import { FONT_FAMILY_UI } from "../../../theme/typography";

// =============================================================================
// ESTILOS GLASSMORPHISM PARA FILTROS DE ACTUACIONES
// =============================================================================

/** @deprecated Usar GLASS_COLORS / tokens. Solo primary para enlaces legacy. */
export const COLORS = {
    primary: GLASS_COLORS.primary,
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
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 700,
  fontSize: "18px",
  color: GLASS_COLORS.textPrimary,
  mb: 2,
};

export const filtroSectionTitleStyles: SxProps<Theme> = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 600,
  fontSize: "15px",
  color: "text.primary",
  mb: 0.75,
};

export const filtroHintStyles: SxProps<Theme> = {
  color: GLASS_COLORS.textSecondary,
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
    color: GLASS_COLORS.textSecondary,
    fontFamily: FONT_FAMILY_UI,
    "&.Mui-focused": { color: GLASS_COLORS.primary },
  },
  "& .MuiInputBase-root": {
    backgroundColor: `var(${V.surfaceInput})`,
    color: `var(${V.textPrimary})`,
    fontFamily: FONT_FAMILY_UI,
    borderRadius: 3,
    "& input": {
      color: `var(${V.textPrimary})`,
      "&::placeholder": { color: `var(${V.textMuted})`, opacity: 1 },
    },
    "& .MuiSvgIcon-root": { color: `var(${V.textSecondary})` },
    "&:hover": {
      backgroundColor: `var(${V.actionHover})`,
      "& .MuiOutlinedInput-notchedOutline": {
        borderColor: GLASS_COLORS.borderMedium,
      },
    },
    "&.Mui-focused": {
      backgroundColor: `var(${V.surfaceInput})`,
      "& .MuiOutlinedInput-notchedOutline": {
        borderColor: GLASS_COLORS.primary,
      },
    },
  },
  "& .MuiOutlinedInput-notchedOutline": {
    borderColor: GLASS_COLORS.borderLight,
  },
  "& .MuiMenuItem-root": {
    backgroundColor: `var(${V.surfacePanelElevated})`,
    color: `var(${V.textPrimary})`,
    "&:hover": {
      backgroundColor: `var(${V.actionHover})`,
    },
    "&.Mui-selected": {
      backgroundColor: `var(${V.actionSelected})`,
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
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 600,
  fontSize: "14px",
  backgroundColor: GLASS_COLORS.primary,
  color: `var(${V.textInverse})`,
  textTransform: "none",
  padding: "10px 24px",
  borderRadius: "6px",
  border: `1px solid ${GLASS_COLORS.borderActive}`,
  boxShadow: `var(${V.shadowPanel})`,
  "&:hover": {
    backgroundColor: `var(${V.actionPrimaryHover})`,
  },
  "&.Mui-disabled": {
    backgroundColor: `var(${V.actionSelected})`,
    color: `var(${V.textDisabled})`,
    borderColor: GLASS_COLORS.borderLight,
  },
};

export const filtroButtonSecondaryStyles: SxProps<Theme> = {
  fontFamily: FONT_FAMILY_UI,
  fontWeight: 600,
  fontSize: "14px",
  backgroundColor: "transparent",
  color: GLASS_COLORS.textPrimary,
  textTransform: "none",
  padding: "10px 24px",
  borderRadius: "6px",
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
  "&:hover": {
    backgroundColor: `var(${V.actionHover})`,
    borderColor: GLASS_COLORS.borderMedium,
  },
  "&.Mui-disabled": {
    color: `var(${V.textDisabled})`,
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
    fontFamily: FONT_FAMILY_UI,
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
  fontFamily: FONT_FAMILY_UI,
  border: `1px solid ${GLASS_COLORS.borderMedium}`,
  borderRadius: "12px",
  mb: 2,
  backgroundColor: GLASS_COLORS.cardBg,
  color: GLASS_COLORS.textPrimary,
  "& .MuiAlert-icon": { color: GLASS_COLORS.textSecondary },
  "& .MuiAlert-message": { fontFamily: FONT_FAMILY_UI },
};

export const errorAlertStyles: SxProps<Theme> = {
  mb: 2,
  backgroundColor: GLASS_COLORS.cardBg,
  color: GLASS_COLORS.textPrimary,
  border: `1px solid var(${V.statusError})`,
  borderRadius: "12px",
  "& .MuiAlert-icon": {
    color: `var(${V.statusError})`,
  },
  "& .MuiAlert-message": {
    fontFamily: FONT_FAMILY_UI,
  },
};
