/**
 * Estilos específicos para CargarRelevamientos
 * Contenedor de grilla al 100% del ancho útil; sin caja gris sólida detrás (fondo transparente).
 */

import { dataViewportFrameSx } from "../../../styles/dataViewportFrame";
import { GLASS_COLORS } from "../../../styles/GlassStyles";
import { GRID_DIMENSIONS } from "../../CargarActuaciones/config/gridTheme";

/**
 * Altura del viewport de la grilla acorde a filas reales (+ header de grupo, fila trailing).
 * No usa el minHeight global de 400px de Cargar actas (evita “filas fantasma” vacías abajo).
 */
export function calculateRelevamientoTableHeight(rowCount: number): number {
    const { rowHeight, headerHeight, groupHeaderHeight, trailingRowHeight, maxHeightOffset } = GRID_DIMENSIONS;
    const contentHeight = groupHeaderHeight + headerHeight + rowCount * rowHeight + trailingRowHeight;
    const maxHeight = typeof window !== "undefined" ? window.innerHeight - maxHeightOffset : 2000;
    const floor = 120;
    return Math.min(Math.max(contentHeight, floor), maxHeight);
}

// =============================================================================
// PALETA DE COLORES
// =============================================================================
export const COLORS = {
    primary: "#0166FF",
    white: "#FFFFFF",
    grayDark: "#2B2E34",
    border: "#3a3d44",
};

// =============================================================================
// CONTENEDORES
// =============================================================================
export const containerStyles = {
    width: "100%",
    minWidth: 0,
    height: "100%",
    fontFamily: '"Tactic Sans", sans-serif',
};

// Sin padding horizontal: el padre (Cargar relevamiento) ya aplica p:{xs:2,sm:3}; evita doble márgen vs el Paper.
export const wrapperStyles = {
    width: "100%",
    minWidth: 0,
    height: "89%",
    display: "flex",
    padding: 0,
    gap: 2,
    boxSizing: "border-box",
    flexDirection: "column" as const,
    alignItems: "stretch",
};

// =============================================================================
// CONTENEDOR DE GRILLA — mismo marco que `dataViewportFrameSx` (baseline Cargar relevamiento)
// =============================================================================
export const gridContainerStyles = dataViewportFrameSx;

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
    backgroundColor: COLORS.primary,
    color: COLORS.white,
    border: `1px solid ${COLORS.primary}`,
    "&:hover": {
        backgroundColor: "#0155DD",
    },
    "&.Mui-disabled": {
        backgroundColor: "rgba(255, 255, 255, 0.08)",
        color: "rgba(255, 255, 255, 0.3)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
    },
};
