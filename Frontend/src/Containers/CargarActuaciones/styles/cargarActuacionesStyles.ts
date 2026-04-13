/**
 * Estilos Glassmorphism para CargarActuaciones
 * Paleta de colores y constantes de diseño
 */

import { m } from "framer-motion";
import { dataViewportFrameSx } from "../../../styles/dataViewportFrame";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

// =============================================================================
// PALETA DE COLORES (mantiene compatibilidad + glass)
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
// ESTILOS DE CONTENEDORES - Glassmorphism
// =============================================================================
export const containerStyles = {
    width: "100%",
    height: "100%",
    fontFamily: '"Tactic Sans", sans-serif',
};

export const wrapperStyles = {
    width: "99%",
    height: "91%",
    display: "flex",
    padding: { xs: 2, sm: 1 },
    flexDirection: "column" as const,
};

// =============================================================================
// ESTILOS DE TÍTULO (removido - ahora en breadcrumb del AppLayout)
// =============================================================================
export const titleStyles = {
    display: "none", // Oculto - el título ahora está en el header del AppLayout
};

// =============================================================================
// ESTILOS DE ALERTAS - Sin blur para rendimiento
// =============================================================================
export const alertBaseStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    border: `1px solid ${GLASS_COLORS.borderMedium}`,
    borderRadius: "10px",
    marginBottom: "16px",
    backgroundColor: GLASS_COLORS.cardBg,
    color: COLORS.white,
    "& .MuiAlert-icon": { color: COLORS.white },
    "& .MuiAlert-message": { fontFamily: '"Tactic Sans", sans-serif' },
};

// =============================================================================
// ESTILOS DEL CONTENEDOR DE GRILLA — alineado a `/cargarRelevamiento` (`dataViewportFrameSx`)
// =============================================================================
export const gridContainerStyles = dataViewportFrameSx;

// =============================================================================
// ESTILOS DE LEYENDA - Sin blur para rendimiento
// =============================================================================
export const legendStyles = {
    marginTop: "20px",
    padding: "20px",
    backgroundColor: GLASS_COLORS.cardBg,
    borderRadius: "12px",
    border: `1px solid ${GLASS_COLORS.borderLight}`,
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
    color: GLASS_COLORS.textSecondary,
    lineHeight: 1.8,
};

export const kbdStyles: React.CSSProperties = {
    padding: "3px 8px",
    backgroundColor: "rgba(0, 0, 0, 0.3)",
    border: `1px solid ${GLASS_COLORS.borderMedium}`,
    borderRadius: "6px",
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 500,
    fontSize: "12px",
    boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
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
    border: `1px solid ${GLASS_COLORS.borderMedium}`,
    borderRadius: "6px",
    marginRight: "8px",
    fontWeight: 600,
});

// =============================================================================
// BOTÓN MANDAR TODO - Azul cuando activo
// =============================================================================
export const buttonMandarTodoStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 600,
    fontSize: "14px",
    textTransform: "none" as const,
    borderRadius: "8px",
    padding: "10px 24px",
    transition: "all 0.2s ease",
    // Estilo activo (enabled)
    backgroundColor: COLORS.primary,
    color: COLORS.white,
    border: `1px solid ${COLORS.primary}`,
    "&:hover": {
        backgroundColor: "#0155DD",
    },
    // Estilo disabled
    "&.Mui-disabled": {
        backgroundColor: "rgba(255, 255, 255, 0.08)",
        color: "rgba(255, 255, 255, 0.3)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
    },
};
