/**
 * Estilos Neo-Brutalistas para la tabla de Actuaciones
 * Tema oscuro coherente con CargarActuaciones (Glide Data Grid)
 * Librería: Material React Table
 */

import type React from "react";
import type { MRT_TableOptions } from "material-react-table";

// =============================================================================
// PALETA DE COLORES NEO-BRUTALISTA (igual que CargarActuaciones)
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
    error: "#E53935",
    errorLight: "#5C2323",
    warning: "#FF9800",
    warningLight: "#3D2E1E",
    rowEven: "#2B2E34",
    rowOdd: "#1E2127",
    border: "#3a3d44",
} as const;

// =============================================================================
// ESTILOS DEL CONTENEDOR PRINCIPAL
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
    paddingBottom: "20px",
};

// =============================================================================
// ESTILOS DEL TÍTULO NEO-BRUTALISTA
// =============================================================================

export const titleStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 800,
    fontSize: { xs: "22px", sm: "38px", md: "52px" },
    color: COLORS.white,
    textShadow: `
        -1px -1px 0 ${COLORS.black},
        1px -1px 0 ${COLORS.black},
        -1px 1px 0 ${COLORS.black},
        1px 1px 0 ${COLORS.black},
        3px 3px 0 ${COLORS.black}
    `,
    letterSpacing: "2px",
    marginBottom: "16px",
};

// =============================================================================
// CONFIGURACIÓN NEO-BRUTALISTA PARA MATERIAL REACT TABLE
// Tema oscuro completo con texto blanco
// =============================================================================

export const DARK_TABLE_CONFIG: Partial<MRT_TableOptions<any>> = {
    // =========================================================================
    // FUNCIONALIDADES HABILITADAS
    // =========================================================================
    enableEditing: true,
    editDisplayMode: "cell" as const,
    enableFullScreenToggle: false,
    enableDensityToggle: false,
    enableSelectAll: true,
    enableRowSelection: true,
    enableColumnFilters: true,      // Filtros por columna ✓
    enableGlobalFilter: true,       // Buscador global ✓
    enablePagination: true,         // Paginación ✓
    enableSorting: true,            // Ordenamiento ✓
    enableHiding: true,             // Ocultar/mostrar columnas ✓

    // =========================================================================
    // FUNCIONALIDADES DESHABILITADAS (no necesarias por ahora)
    // =========================================================================
    enableGrouping: false,          // GroupBy deshabilitado
    enableColumnDragging: false,    // Mover columnas deshabilitado
    enableColumnOrdering: false,    // Reordenar columnas deshabilitado

    // =========================================================================
    // OPTIMIZACIÓN DE RENDIMIENTO
    // =========================================================================
    enableRowVirtualization: false,
    enableColumnVirtualization: false,
    positionToolbarAlertBanner: "bottom",
    
    // Filtro global optimizado
    globalFilterFn: "contains",
    filterFns: {
        contains: (row, columnId, filterValue) => {
            const value = row.getValue(columnId);
            return value != null && String(value).toLowerCase().includes(String(filterValue).toLowerCase());
        },
    },

    // =========================================================================
    // BANNER DE ALERTA (X rows selected) - Fondo oscuro SIN azul
    // =========================================================================
    muiToolbarAlertBannerProps: {
        sx: {
            backgroundColor: COLORS.grayDark,
            color: COLORS.white,
            border: `1px solid ${COLORS.border}`,
            fontFamily: '"Tactic Sans", sans-serif',
            fontSize: "12px",
            "& .MuiAlert-message": {
                color: COLORS.white,
            },
            "& .MuiAlert-icon": {
                color: COLORS.white,
            },
            "& .MuiButton-root": {
                color: COLORS.white,
                "&:hover": {
                    color: COLORS.primary,
                },
            },
        },
    },

    // =========================================================================
    // TOOLBAR SUPERIOR - Fondo oscuro, iconos blancos con hover azul
    // SIN animaciones lentas
    // =========================================================================
    muiTopToolbarProps: {
        sx: {
            backgroundColor: COLORS.grayDark,
            borderBottom: `1px solid ${COLORS.border}`,
            padding: "8px 16px",
            "& .MuiIconButton-root": {
                color: COLORS.white,
                transition: "none",  // Sin animación para velocidad
                "&:hover": {
                    color: COLORS.primary,
                    backgroundColor: "rgba(1, 102, 255, 0.1)",
                },
            },
            "& .MuiInputBase-root": {
                backgroundColor: COLORS.rowOdd,
                color: COLORS.white,
                borderRadius: "8px",
                border: `1px solid ${COLORS.border}`,
                transition: "none",  // Sin animación
                "& input": {
                    color: COLORS.white,
                    "&::placeholder": {
                        color: "#999",
                        opacity: 1,
                    },
                },
                "& .MuiSvgIcon-root": {
                    color: COLORS.white,
                },
            },
            "& .MuiButton-root": {
                color: COLORS.white,
                fontFamily: '"Tactic Sans", sans-serif',
            },
        },
    },

    // =========================================================================
    // TOOLBAR INFERIOR - Fondo oscuro (paginación) - SIN animaciones
    // =========================================================================
    muiBottomToolbarProps: {
        sx: {
            backgroundColor: COLORS.grayDark,
            borderTop: `1px solid ${COLORS.border}`,
            "& .MuiTablePagination-root": {
                color: COLORS.white,
            },
            "& .MuiIconButton-root": {
                color: COLORS.white,
                transition: "none",  // Sin animación
                "&:hover": {
                    color: COLORS.primary,
                    backgroundColor: "rgba(1, 102, 255, 0.15)",
                },
                "&.Mui-disabled": {
                    color: "#555",
                },
            },
            "& .MuiSelect-select": {
                color: COLORS.white,
            },
            "& .MuiSelect-icon": {
                color: COLORS.white,
            },
            "& .MuiTablePagination-displayedRows": {
                color: COLORS.white,
                fontFamily: '"Tactic Sans", sans-serif',
            },
            "& .MuiTablePagination-selectLabel": {
                color: COLORS.white,
                fontFamily: '"Tactic Sans", sans-serif',
            },
        },
    },

    // =========================================================================
    // CABECERAS DE COLUMNA - Fondo oscuro con texto blanco
    // =========================================================================
    muiTableHeadCellProps: {
        sx: {
            backgroundColor: COLORS.grayDark,
            color: COLORS.white,
            fontWeight: 600,
            fontSize: "12px",
            fontFamily: '"Tactic Sans", sans-serif',
            borderBottom: `1px solid ${COLORS.border}`,
            borderRight: `1px solid ${COLORS.border}`,
            padding: "12px 8px",
            "& .MuiTableSortLabel-root": {
                color: COLORS.white,
                "&:hover": {
                    color: COLORS.primary,
                },
                "&.Mui-active": {
                    color: COLORS.primary,
                    "& .MuiTableSortLabel-icon": {
                        color: COLORS.primary,
                    },
                },
            },
            "& .MuiCheckbox-root": {
                color: COLORS.white,
                "&.Mui-checked": {
                    color: COLORS.primary,
                },
            },
            "& .MuiIconButton-root": {
                color: COLORS.white,
                transition: "none",  // Sin animación
                "&:hover": {
                    color: COLORS.primary,
                    backgroundColor: "rgba(1, 102, 255, 0.15)",
                },
            },
            "& .MuiInputBase-root": {
                color: COLORS.white,
                backgroundColor: COLORS.rowOdd,
                borderRadius: "4px",
                fontSize: "11px",
                "& input": {
                    color: COLORS.white,
                    padding: "4px 8px",
                },
            },
        },
    },

    // =========================================================================
    // CELDAS DEL CUERPO - Fondo oscuro alternado - SIN animaciones
    // =========================================================================
    muiTableBodyCellProps: ({ row }) => ({
        sx: {
            backgroundColor: row.index % 2 === 0 ? COLORS.rowEven : COLORS.rowOdd,
            color: COLORS.white,
            fontSize: "11px",
            fontFamily: '"Tactic Sans", sans-serif',
            borderBottom: `1px solid ${COLORS.border}`,
            borderRight: `1px solid ${COLORS.border}`,
            padding: "8px",
            "& .MuiCheckbox-root": {
                color: COLORS.white,
                "&.Mui-checked": {
                    color: COLORS.primary,
                },
            },
            "& .MuiIconButton-root": {
                color: COLORS.white,
                transition: "none",  // Sin animación para velocidad
                "&:hover": {
                    color: COLORS.primary,
                    backgroundColor: "rgba(1, 102, 255, 0.15)",
                },
            },
            // Input de edición
            "& .MuiInputBase-root": {
                color: COLORS.white,
                backgroundColor: COLORS.rowOdd,
                borderRadius: "4px",
                border: `1px solid ${COLORS.primary}`,
                "& input": {
                    color: COLORS.white,
                },
            },
        },
    }),

    // =========================================================================
    // FILAS - Hover oscuro - SIN animaciones, selección instantánea
    // =========================================================================
    muiTableBodyRowProps: ({ row }) => ({
        sx: {
            backgroundColor: row.index % 2 === 0 ? COLORS.rowEven : COLORS.rowOdd,
            transition: "none",  // IMPORTANTE: Sin animación = selección instantánea
            "&:hover": {
                backgroundColor: "#3a3d44",
            },
            "&.Mui-selected": {
                backgroundColor: "#1a3a5c !important",  // Force sin animación
                "& td": {
                    backgroundColor: "#1a3a5c !important",
                },
                "&:hover": {
                    backgroundColor: "#1a4a6c !important",
                },
            },
        },
    }),

    // =========================================================================
    // CONTENEDOR DE LA TABLA
    // =========================================================================
    muiTableContainerProps: {
        sx: {
            maxHeight: "calc(100vh - 350px)",
            minHeight: "300px",
            backgroundColor: COLORS.grayDark,
            border: `1px solid ${COLORS.border}`,
            borderRadius: "8px",
            // Scrollbar oscuro
            "&::-webkit-scrollbar": {
                width: "8px",
                height: "8px",
            },
            "&::-webkit-scrollbar-track": {
                background: COLORS.rowOdd,
            },
            "&::-webkit-scrollbar-thumb": {
                backgroundColor: COLORS.border,
                borderRadius: "4px",
            },
            "&::-webkit-scrollbar-thumb:hover": {
                backgroundColor: "#4a4d54",
            },
        },
    },

    // =========================================================================
    // PAPER PRINCIPAL
    // =========================================================================
    muiTablePaperProps: {
        sx: {
            backgroundColor: COLORS.grayDark,
            boxShadow: "0px 3px 1px -2px rgba(0,0,0,0.2), 0px 2px 2px 0px rgba(0,0,0,0.14), 0px 1px 5px 0px rgba(0,0,0,0.12)",
            border: `1px solid ${COLORS.border}`,
            borderRadius: "8px",
            overflow: "hidden",
        },
    },

    // =========================================================================
    // TABLA BASE
    // =========================================================================
    muiTableProps: {
        sx: {
            backgroundColor: COLORS.grayDark,
            tableLayout: "fixed",
        },
    },

    // =========================================================================
    // CELDA DE CABECERA DE GRUPO
    // =========================================================================
    muiTableHeadRowProps: {
        sx: {
            backgroundColor: COLORS.grayDark,
            "& th": {
                backgroundColor: COLORS.grayDark,
            },
        },
    },
};

// =============================================================================
// ESTILOS DE BOTONES DE EXPORTACIÓN NEO-BRUTALISTAS
// =============================================================================

export const exportBoxStyles = {
    display: "flex",
    gap: "10px",
    padding: "8px",
    flexDirection: { xs: "column", md: "row" },
};

export const exportButtonStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 500,
    fontSize: "12px",
    textTransform: "none" as const,
    color: COLORS.white,
    backgroundColor: COLORS.rowOdd,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "6px",
    padding: "6px 12px",
    transition: "none",  // Sin animación
    "&:hover": {
        backgroundColor: "rgba(1, 102, 255, 0.15)",
        color: COLORS.primary,
        borderColor: COLORS.primary,
    },
    "&:disabled": {
        color: "#555",
        backgroundColor: COLORS.rowOdd,
    },
    "& .MuiButton-startIcon": {
        color: "inherit",
    },
};

// =============================================================================
// ESTILOS DE LOADING
// =============================================================================

export const loadingStyles = {
    display: "flex",
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: { xs: "20px", md: "28px" },
    fontWeight: 700,
    color: COLORS.white,
    justifyContent: "center",
    alignItems: "center",
    marginTop: "20%",
    textShadow: `0 0 20px ${COLORS.primary}`,
};

// =============================================================================
// ESTILOS DE LA LEYENDA "CÓMO USAR"
// Fondo oscuro #2B2E34 con texto blanco (coherente con CargarActuaciones)
// =============================================================================

export const legendStyles = {
    marginTop: "16px",
    padding: "16px 20px",
    backgroundColor: COLORS.grayDark,
    borderRadius: "8px",
    border: `1px solid ${COLORS.border}`,
    boxShadow: "0px 2px 4px rgba(0,0,0,0.3)",
};

export const legendTitleStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 700,
    fontSize: "14px",
    marginBottom: "10px",
    color: COLORS.white,
};

export const legendTextStyles = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 400,
    fontSize: "12px",
    color: COLORS.white,
    lineHeight: 1.9,
};

/** Estilos para iconos/botones en la leyenda */
export const legendIconStyles: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "4px 8px",
    backgroundColor: COLORS.rowOdd,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "4px",
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 500,
    fontSize: "11px",
    marginLeft: "4px",
    marginRight: "4px",
    color: COLORS.white,
    verticalAlign: "middle",
};

/** Estilos para teclas (kbd) en la leyenda */
export const kbdStyles: React.CSSProperties = {
    padding: "2px 6px",
    backgroundColor: COLORS.rowOdd,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "4px",
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 500,
    fontSize: "11px",
    boxShadow: "1px 1px 0 #000",
    display: "inline-block",
    marginLeft: "4px",
    marginRight: "4px",
    color: COLORS.white,
};
