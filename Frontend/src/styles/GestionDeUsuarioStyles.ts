import type { MRT_TableOptions } from "material-react-table";

export const TablaGestionUsuariosStyle: Partial<MRT_TableOptions<any>> = {
    enableRowSelection: false,
    enableColumnFilters: false,
    enableSorting: true,
    enablePagination: true,
    enableGlobalFilter: true,
    enableDensityToggle: false,
    enableFullScreenToggle: false,
    enableColumnDragging: false,
    enableGrouping: false,
    enableColumnResizing: false,
    positionGlobalFilter: "right",
    // 🔵 TOP TOOLBAR
    muiTopToolbarProps: {
        sx: {
            flexDirection: { xs: "column", md: "row" },
            backgroundColor: "#2B2E34",
            borderBottom: "1px solid #3a3d44",
            "& .MuiIconButton-root": {
                color: "#FFFFFF",
                transition: "color 0.2s ease",
                "&:hover": {
                    color: "#0166FF",
                    backgroundColor: "rgba(1, 102, 255, 0.1)",
                },
            },
            "& .MuiInputBase-root": {
                backgroundColor: "#1E2127",
                color: "#FFFFFF",
                "& input": {
                    color: "#FFFFFF",
                    "&::placeholder": { color: "#999", opacity: 1 },
                },
                "& .MuiSvgIcon-root": { color: "#FFFFFF" },
            },
        },
    },

    // 🔵 BOTTOM TOOLBAR
    muiBottomToolbarProps: {
        sx: {
            backgroundColor: "#2B2E34",
            borderTop: "1px solid #3a3d44",
            "& .MuiTablePagination-root": { color: "#FFFFFF" },
            "& .MuiIconButton-root": {
                color: "#FFFFFF",
                "&:hover": {
                    color: "#0166FF",
                    backgroundColor: "rgba(1, 102, 255, 0.15)",
                },
                "&.Mui-disabled": { color: "#555" },
            },
            "& .MuiSelect-select": { color: "#FFFFFF" },
            "& .MuiSelect-icon": { color: "#FFFFFF" },
        },
    },

    // 🔵 HEADER
    muiTableHeadCellProps: {
        sx: {
            backgroundColor: "#2B2E34",
            color: "#FFFFFF",
            fontWeight: 600,
            fontSize: "15px",
            fontFamily: '"Tactic Sans", sans-serif',
            borderBottom: "1px solid #3a3d44",
            borderRight: "1px solid #3a3d44",
            "& .MuiTableSortLabel-root": {
                color: "#FFFFFF",
                "&:hover": { color: "#0166FF" },
                "&.Mui-active": {
                    color: "#0166FF",
                    "& .MuiTableSortLabel-icon": { color: "#0166FF" },
                },
            },
            "& .MuiIconButton-root": {
                color: "#FFFFFF",
                "&:hover": {
                    color: "#0166FF",
                    backgroundColor: "rgba(1, 102, 255, 0.15)",
                },
            },
        },
    },

    // 🔵 CELDAS
    muiTableBodyCellProps: ({ row } : { row: any }) => ({
        sx: {
            backgroundColor: row.index % 2 === 0 ? "#2B2E34" : "#1E2127",
            color: "#FFFFFF",
            fontSize: "13px",
            fontFamily: '"Tactic Sans", sans-serif',
            borderBottom: "1px solid #3a3d44",
            borderRight: "1px solid #3a3d44",
            transition: "none",
        },
    }),

    // 🔵 FILAS
    muiTableBodyRowProps: ({ row } : { row: any }) => ({
        sx: {
            backgroundColor: row.index % 2 === 0 ? "#2B2E34" : "#1E2127",
            "&:hover": { backgroundColor: "#3a3d44" },
            transition: "none",
        },
    }),

    // 🔵 CONTENEDOR
    muiTableContainerProps: {
        sx: {
            maxHeight: "calc(100vh - 350px)",
            minHeight: "300px",
            backgroundColor: "#2B2E34",
            border: "1px solid #3a3d44",
            borderRadius: "8px",
            "&::-webkit-scrollbar": { width: "8px", height: "8px" },
            "&::-webkit-scrollbar-track": { background: "#1E2127" },
            "&::-webkit-scrollbar-thumb": {
                backgroundColor: "#3a3d44",
                borderRadius: "4px",
            },
            "&::-webkit-scrollbar-thumb:hover": {
                backgroundColor: "#4a4d54",
            },
        },
    },

    muiTablePaperProps: {
        sx: {
            backgroundColor: "#2B2E34",
            boxShadow:
                "0px 3px 1px -2px rgba(0,0,0,0.2), 0px 2px 2px 0px rgba(0,0,0,0.14), 0px 1px 5px 0px rgba(0,0,0,0.12)",
            border: "1px solid #3a3d44",
            borderRadius: "8px",
            overflow: "hidden",
        },
    },
}
