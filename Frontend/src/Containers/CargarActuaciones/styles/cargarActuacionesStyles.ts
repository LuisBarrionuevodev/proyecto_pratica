/**
 * Estilos Neo-Brutalistas para CargarActuaciones
 * Paleta de colores y constantes de diseño
 */

// =============================================================================
// PALETA DE COLORES
// =============================================================================
export const COLORS = {
    primary: "#0166FF",
    black: "#000000",
    white: "#FFFFFF",
    grayDark: "#2B2E34",
    grayMedium: "#353535",
    grayLight: "#D9D9D9",
    grayLighter: "#F5F5F5",
    success: "#2D9F4B",
    successLight: "#1E3D2F",
    successText: "#6BFF6B",
    error: "#E53935",
    errorLight: "#5C2323",
    errorText: "#FF6B6B",
    warning: "#FF9800",
    warningLight: "#3D2E1E",
    warningText: "#FFD700",
    rowEven: "#2B2E34",
    rowOdd: "#1E2127",
    border: "#3a3d44",
};

// =============================================================================
// ESTILOS DE CONTENEDORES
// =============================================================================
export const containerStyles = {
    width: "100%",
    height: "100%",
    fontFamily: '"Tactic Sans", sans-serif',
};

export const wrapperStyles = {
    width: { xs: "280px", sm: "520px", md: "920px", lg: "920px", xl: "1220px" },
    display: "flex",
    position: "absolute" as const,
    top: { xs: "10px", sm: "1%", md: "5%", lg: "5%", xl: "8%" },
    marginLeft: { xs: "90px", sm: "100px", md: "100px", lg: "120px", xl: "100px" },
    textAlign: "center" as const,
    justifySelf: "center",
    flexDirection: "column" as const,
};

// =============================================================================
// ESTILOS DE TÍTULO
// =============================================================================
export const titleStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 800,
    fontSize: { xs: "22px", sm: "38px", md: "52px" },
    color: COLORS.white,
    textShadow: `2px 2px 4px rgba(0, 0, 0, 0.5)`,
    letterSpacing: "2px",
    marginBottom: "16px",
};

// =============================================================================
// ESTILOS DE ALERTAS
// =============================================================================
export const alertBaseStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    border: `1px solid ${COLORS.border}`,
    borderRadius: "8px",
    marginBottom: "16px",
    backgroundColor: COLORS.grayDark,
    color: COLORS.white,
    boxShadow: "0px 2px 4px rgba(0,0,0,0.3)",
    "& .MuiAlert-icon": { color: COLORS.white },
    "& .MuiAlert-message": { fontFamily: '"Tactic Sans", sans-serif' },
};

// =============================================================================
// ESTILOS DEL CONTENEDOR DE GRILLA
// =============================================================================
export const gridContainerStyles = {
    border: `1px solid ${COLORS.border}`,
    borderRadius: "8px",
    overflow: "hidden",
    boxShadow: "0px 3px 1px -2px rgba(0,0,0,0.2), 0px 2px 2px 0px rgba(0,0,0,0.14), 0px 1px 5px 0px rgba(0,0,0,0.12)",
    backgroundImage: "linear-gradient(rgba(255, 255, 255, 0.069), rgba(255, 255, 255, 0.069))",
    backgroundColor: COLORS.grayDark,
};

// =============================================================================
// ESTILOS DE LEYENDA
// =============================================================================
export const legendStyles = {
    marginTop: "16px",
    marginBottom: "8px",
    padding: "20px",
    backgroundColor: COLORS.grayDark,
    borderRadius: "8px",
    border: `1px solid #1A1C20`,
    boxShadow: "0px 2px 4px rgba(0,0,0,0.3)",
};

export const legendTitleStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 700,
    fontSize: "16px",
    marginBottom: "12px",
    color: COLORS.white,
};

export const legendTextStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 400,
    fontSize: "14px",
    color: COLORS.white,
    lineHeight: 1.8,
};

export const kbdStyles: React.CSSProperties = {
    padding: "3px 8px",
    backgroundColor: "#1A1C20",
    border: `1px solid #555`,
    borderRadius: "4px",
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 500,
    fontSize: "12px",
    boxShadow: "1px 1px 0 #000",
    display: "inline-block",
    marginLeft: "4px",
    marginRight: "4px",
    color: COLORS.white,
};

export const getStatusBadgeStyles = (bgColor: string, textColor: string): React.CSSProperties => ({
    display: "inline-block",
    padding: "2px 8px",
    backgroundColor: bgColor,
    color: textColor,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "4px",
    marginRight: "8px",
    fontWeight: 600,
});
