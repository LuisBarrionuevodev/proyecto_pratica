import type { SxProps, Theme } from "@mui/material";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

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
  gap: 2,
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
};

// Título oculto (ahora en el breadcrumb del AppLayout)
export const titleStyles: SxProps<Theme> = {
    display: "none",
};

// =============================================================================
// CONTENEDOR DE FILTROS - Sin blur para rendimiento
// =============================================================================

export const filtroContainerStyles: SxProps<Theme> = {
    marginBottom: "20px",
    padding: "24px",
    backgroundColor: GLASS_COLORS.cardBg,
    borderRadius: "12px",
    border: `1px solid ${GLASS_COLORS.borderLight}`,
};

export const filtroTitleStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 700,
    fontSize: "18px",
    color: COLORS.white,
    marginBottom: "20px",
};

export const filtroGridStyles: SxProps<Theme> = {
    display: "grid",
    gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" },
    gap: "16px",
    marginBottom: "16px",
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
            "&::placeholder": { color: "#999", opacity: 1 },
        },
        "& .MuiSvgIcon-root": { color: COLORS.white },
        "&:hover": {
            backgroundColor: COLORS.grayMedium,
        },
        "&.Mui-focused": {
            backgroundColor: COLORS.grayMedium,
            "& .MuiOutlinedInput-notchedOutline": {
                borderColor: COLORS.primary,
            },
        },
    },
    "& .MuiOutlinedInput-notchedOutline": {
        borderColor: COLORS.border,
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
    gap: "12px",
    justifyContent: "flex-end",
};

export const filtroButtonPrimaryStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 600,
    fontSize: "14px",
    backgroundColor: COLORS.primary,
    color: COLORS.white,
    textTransform: "none",
    padding: "10px 24px",
    borderRadius: "6px",
    border: `1px solid ${COLORS.border}`,
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
    border: `1px solid ${COLORS.border}`,
    "&:hover": {
        backgroundColor: COLORS.rowOdd,
        borderColor: COLORS.white,
    },
};

// =============================================================================
// METADATA E INFO - Sin blur para rendimiento
// =============================================================================

export const metaInfoStyles: SxProps<Theme> = {
    marginBottom: "16px",
    padding: "12px 16px",
    backgroundColor: GLASS_COLORS.cardBg,
    borderRadius: "10px",
    border: `1px solid ${GLASS_COLORS.borderLight}`,
    display: "flex",
    alignItems: "center",
    gap: "16px",
    flexWrap: "wrap",
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

/** Estilo canónico para alertas en fondos dark institucionales. Referencia: CargarActuaciones. */
export const alertBaseStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    border: `1px solid ${COLORS.border}`,
    borderRadius: "10px",
    marginBottom: "16px",
    backgroundColor: COLORS.grayDark,
    color: COLORS.white,
    "& .MuiAlert-icon": { color: COLORS.white },
    "& .MuiAlert-message": { fontFamily: '"Tactic Sans", sans-serif' },
};

export const errorAlertStyles: SxProps<Theme> = {
    marginBottom: "16px",
    backgroundColor: "rgba(92, 35, 35, 0.9)",
    color: COLORS.white,
    border: `1px solid ${COLORS.error}`,
    borderRadius: "10px",
    "& .MuiAlert-icon": {
        color: COLORS.error,
    },
    "& .MuiAlert-message": {
        fontFamily: '"Tactic Sans", sans-serif',
    },
};
