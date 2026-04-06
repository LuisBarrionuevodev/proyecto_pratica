import type { MRT_TableOptions } from "material-react-table";
import type { SxProps, Theme } from "@mui/material";

/**
 * Bandejas / listados solo lectura: sin edición ni selección de filas (formularios en modal glass).
 * Combinar con spread: `useMaterialReactTable({ ...DARK_TABLE_CONFIG, ...MRT_READ_ONLY_BANDEJA, ... })`
 */
export const MRT_READ_ONLY_BANDEJA: Partial<MRT_TableOptions<any>> = {
  enableEditing: false,
  enableRowSelection: false,
  enableSelectAll: false,
};

// =============================================================================
// ESTILOS NEO-BRUTALISTAS PARA ACTUACIONES - Material React Table
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

// Configuración completa de la tabla con tema oscuro
export const DARK_TABLE_CONFIG: Partial<MRT_TableOptions<any>> = {
    enableEditing: true,
    editDisplayMode: "cell" as const,
    enableFullScreenToggle: false,
    enableDensityToggle: false,
    enableSelectAll: true,
    enableRowSelection: true,
    enableColumnFilters: true,
    enableGlobalFilter: true,
    enablePagination: true,
    enableSorting: true,
    enableColumnDragging: false,
    enableGrouping: false,
    enableColumnResizing: false,
    globalFilterFn: "contains",
    positionToolbarAlertBanner: "bottom",

    muiTopToolbarProps: {
        sx: {
            backgroundColor: COLORS.grayDark,
            borderBottom: `1px solid ${COLORS.border}`,
            "& .MuiIconButton-root": {
                color: COLORS.white,
                transition: "color 0.2s ease",
                "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.1)" },
            },
            "& .MuiInputBase-root": {
                backgroundColor: COLORS.rowOdd,
                color: COLORS.white,
                "& input": { color: COLORS.white, "&::placeholder": { color: "#999", opacity: 1 } },
                "& .MuiSvgIcon-root": { color: COLORS.white },
            },
        },
    },

    muiBottomToolbarProps: {
        sx: {
            backgroundColor: COLORS.grayDark,
            borderTop: `1px solid ${COLORS.border}`,
            "& .MuiTablePagination-root": { color: COLORS.white },
            "& .MuiIconButton-root": {
                color: COLORS.white,
                transition: "color 0.2s ease, background-color 0.2s ease",
                "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
                "&.Mui-disabled": { color: "#555" },
            },
            "& .MuiSelect-select": { color: COLORS.white },
            "& .MuiSelect-icon": { color: COLORS.white },
        },
    },

    muiTableHeadCellProps: {
        sx: {
            backgroundColor: COLORS.grayDark,
            color: COLORS.white,
            fontWeight: 600,
            fontSize: "12px",
            fontFamily: '"Tactic Sans", sans-serif',
            borderBottom: `1px solid ${COLORS.border}`,
            borderRight: `1px solid ${COLORS.border}`,
            "& .MuiTableSortLabel-root": { 
                color: COLORS.white, 
                "&:hover": { color: COLORS.primary }, 
                "&.Mui-active": { color: COLORS.primary, "& .MuiTableSortLabel-icon": { color: COLORS.primary } } 
            },
            "& .MuiCheckbox-root": { color: COLORS.white, "&.Mui-checked": { color: COLORS.primary } },
            "& .MuiIconButton-root": {
                color: COLORS.white,
                transition: "color 0.2s ease, background-color 0.2s ease",
                "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
            },
        },
    },

    muiTableBodyCellProps: ({ row }: { row: any }) => ({
        sx: {
            backgroundColor: row.index % 2 === 0 ? COLORS.rowEven : COLORS.rowOdd,
            color: COLORS.white,
            fontSize: "11px",
            fontFamily: '"Tactic Sans", sans-serif',
            borderBottom: `1px solid ${COLORS.border}`,
            borderRight: `1px solid ${COLORS.border}`,
            "& .MuiCheckbox-root": { color: COLORS.white, "&.Mui-checked": { color: COLORS.primary } },
            "& .MuiIconButton-root": {
                color: COLORS.white,
                transition: "color 0.2s ease, background-color 0.2s ease",
                "&:hover": { color: COLORS.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
            },
        },
    }),

    muiTableBodyRowProps: ({ row }: { row: any }) => ({
        sx: {
            backgroundColor: row.index % 2 === 0 ? COLORS.rowEven : COLORS.rowOdd,
            "&:hover": { backgroundColor: "#3a3d44" },
            "&.Mui-selected": {
                backgroundColor: "#1a3a5c",
                "&:hover": { backgroundColor: "#1a4a6c" },
            },
            transition: "none",
        },
    }),

    muiTableContainerProps: {
        sx: {
            maxHeight: "calc(100vh - 350px)",
            minHeight: "300px",
            width: "100%",
            maxWidth: "100%",
            overflowX: "auto",
            overflowY: "auto",
            backgroundColor: COLORS.grayDark,
            border: `1px solid ${COLORS.border}`,
            borderRadius: "8px",
            "&::-webkit-scrollbar": { width: "8px", height: "8px" },
            "&::-webkit-scrollbar-track": { background: COLORS.rowOdd },
            "&::-webkit-scrollbar-thumb": { backgroundColor: COLORS.border, borderRadius: "4px" },
            "&::-webkit-scrollbar-thumb:hover": { backgroundColor: "#4a4d54" },
        },
    },

    muiTablePaperProps: {
        sx: {
            backgroundColor: COLORS.grayDark,
            boxShadow: "0px 3px 1px -2px rgba(0,0,0,0.2), 0px 2px 2px 0px rgba(0,0,0,0.14), 0px 1px 5px 0px rgba(0,0,0,0.12)",
            border: `1px solid ${COLORS.border}`,
            borderRadius: "8px",
            overflow: "hidden",
        },
    },
};

// =============================================================================
// ESTILOS ADICIONALES
// =============================================================================

export const containerStyles: SxProps<Theme> = {
    width: "100%",
    height: "100%",
    fontFamily: '"Tactic Sans", sans-serif',
};

export const wrapperStyles: SxProps<Theme> = {
    width: { xs: "280px", sm: "520px", md: "920px", lg: "920px", xl: "1220px" },
    display: "flex",
    position: "absolute",
    top: { xs: "10px", sm: "1%", md: "5%", lg: "5%", xl: "8%" },
    marginLeft: { xs: "90px", sm: "100px", md: "100px", lg: "120px", xl: "100px" },
    textAlign: "center",
    justifySelf: "center",
    flexDirection: "column",
    paddingBottom: "20px",
};

export const titleStyles: SxProps<Theme> = {
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

export const loadingStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontSize: "18px",
    color: COLORS.white,
    textAlign: "center",
    padding: "40px",
};

export const exportBoxStyles: SxProps<Theme> = {
    display: "flex",
    gap: 1,
    flexWrap: "wrap",
};

export const exportButtonStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 500,
    fontSize: "12px",
    color: COLORS.white,
    borderColor: COLORS.border,
    textTransform: "none",
    "&:hover": {
        color: COLORS.primary,
        borderColor: COLORS.primary,
        backgroundColor: "rgba(1, 102, 255, 0.1)",
    },
};

// =============================================================================
// ESTILOS PARA LA LEYENDA "CÓMO USAR"
// =============================================================================

export const legendStyles: SxProps<Theme> = {
    marginTop: "16px",
    padding: "16px 20px",
    backgroundColor: COLORS.grayDark,
    borderRadius: "8px",
    border: `1px solid #1A1C20`,
    boxShadow: "0px 2px 4px rgba(0,0,0,0.3)",
};

export const legendTitleStyles: SxProps<Theme> = {
    fontFamily: '"Tactic Sans", sans-serif',
    fontWeight: 700,
    fontSize: "16px",
    marginBottom: "12px",
    color: COLORS.white,
};

export const legendTextStyles: SxProps<Theme> = {
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
