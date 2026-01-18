import type { SxProps, Theme } from "@mui/material";

// =============================================================================
// ESTILOS NEO-BRUTALISTAS PARA FILTROS DE ACTUACIONES
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
// LAYOUT PRINCIPAL
// =============================================================================

export const wrapperStyles: SxProps<Theme> = {
    width: { xs: "280px", sm: "520px", md: "920px", lg: "920px", xl: "1220px" },
    display: "flex",
    position: "absolute",
    top: { xs: "10px", sm: "1%", md: "5%", lg: "5%", xl: "8%" },
    marginLeft: { xs: "90px", sm: "100px", md: "100px", lg: "120px", xl: "100px" },
    textAlign: "center",
    justifySelf: "center",
    flexDirection: "column",
};

export const titleStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 800,
    fontSize: { xs: "22px", sm: "38px", md: "52px" },
    color: COLORS.white,
    textShadow: "2px 2px 4px rgba(0, 0, 0, 0.5)",
    letterSpacing: "2px",
    marginBottom: "24px",
    textAlign: "left",
};

// =============================================================================
// CONTENEDOR DE FILTROS
// =============================================================================

export const filtroContainerStyles: SxProps<Theme> = {
    marginBottom: "24px",
    padding: "24px",
    backgroundColor: COLORS.grayDark,
    borderRadius: "8px",
    border: `1px solid ${COLORS.border}`,
    boxShadow: "0px 3px 1px -2px rgba(0,0,0,0.2), 0px 2px 2px 0px rgba(0,0,0,0.14), 0px 1px 5px 0px rgba(0,0,0,0.12)",
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
        borderRadius: "6px",
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
// METADATA E INFO
// =============================================================================

export const metaInfoStyles: SxProps<Theme> = {
    marginBottom: "16px",
    padding: "12px 16px",
    backgroundColor: COLORS.rowOdd,
    borderRadius: "6px",
    border: `1px solid ${COLORS.border}`,
    display: "flex",
    alignItems: "center",
    gap: "16px",
    flexWrap: "wrap",
};

export const metaItemStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: "13px",
    color: COLORS.white,
    "& strong": {
        color: COLORS.primary,
        fontWeight: 600,
    },
};

// =============================================================================
// ALERTS Y ERRORES
// =============================================================================

export const errorAlertStyles: SxProps<Theme> = {
    marginBottom: "16px",
    backgroundColor: "#5C2323",
    color: COLORS.white,
    border: `1px solid ${COLORS.error}`,
    borderRadius: "6px",
    "& .MuiAlert-icon": {
        color: COLORS.error,
    },
    "& .MuiAlert-message": {
        fontFamily: '"Tactic Sans", sans-serif',
    },
};
