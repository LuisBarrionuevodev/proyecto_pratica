import type { SxProps, Theme } from "@mui/material";
import type { MRT_TableOptions } from "material-react-table";

import { GLASS_COLORS } from "./GlassStyles";

/**
 * Paleta compartida para tablas MRT estilo glass / institucional (F3.7b).
 * Alias histórico en pantallas: `COLORS` vía `actuacionesTableStyles.ts`.
 */
export const DATA_TABLE_MRT_GLASS_COLORS = {
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

const C = DATA_TABLE_MRT_GLASS_COLORS;

/**
 * Preset MRT reutilizable: marco glass, toolbar, header, filas, hover, paginación.
 * Las pantallas combinan con spread: `useMaterialReactTable({ ...MRT_DATA_TABLE_GLASS_PRESET, ...overrides })`.
 * Opciones de negocio (edición, filtros, paginación on/off) pueden sobrescribirse después del spread.
 */
export const MRT_DATA_TABLE_GLASS_PRESET: Partial<MRT_TableOptions<any>> = {
  enableFullScreenToggle: false,
  enableDensityToggle: false,
  enableColumnDragging: false,
  enableGrouping: false,
  enableColumnResizing: false,
  globalFilterFn: "contains",
  positionToolbarAlertBanner: "bottom",

  muiTopToolbarProps: {
    sx: {
      backgroundColor: GLASS_COLORS.cardBg,
      borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
      "& .MuiIconButton-root": {
        color: C.white,
        transition: "color 0.2s ease",
        "&:hover": { color: C.primary, backgroundColor: "rgba(1, 102, 255, 0.1)" },
      },
      "& .MuiInputBase-root": {
        backgroundColor: C.rowOdd,
        color: C.white,
        "& input": {
          color: C.white,
          "&::placeholder": { color: GLASS_COLORS.textMuted, opacity: 1 },
        },
        "& .MuiSvgIcon-root": { color: C.white },
      },
    },
  },

  muiBottomToolbarProps: {
    sx: {
      backgroundColor: GLASS_COLORS.cardBg,
      borderTop: `1px solid ${GLASS_COLORS.borderLight}`,
      "& .MuiTablePagination-root": { color: C.white },
      "& .MuiIconButton-root": {
        color: C.white,
        transition: "color 0.2s ease, background-color 0.2s ease",
        "&:hover": { color: C.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
        "&.Mui-disabled": { color: GLASS_COLORS.textMuted },
      },
      "& .MuiSelect-select": { color: C.white },
      "& .MuiSelect-icon": { color: C.white },
    },
  },

  muiTableHeadCellProps: {
    sx: {
      backgroundColor: GLASS_COLORS.cardBg,
      color: C.white,
      fontWeight: 600,
      fontSize: "12px",
      fontFamily: '"Tactic Sans", sans-serif',
      borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
      borderRight: `1px solid ${GLASS_COLORS.borderLight}`,
      "& .MuiTableSortLabel-root": {
        color: C.white,
        "&:hover": { color: C.primary },
        "&.Mui-active": { color: C.primary, "& .MuiTableSortLabel-icon": { color: C.primary } },
      },
      "& .MuiCheckbox-root": { color: C.white, "&.Mui-checked": { color: C.primary } },
      "& .MuiIconButton-root": {
        color: C.white,
        transition: "color 0.2s ease, background-color 0.2s ease",
        "&:hover": { color: C.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
      },
    },
  },

  muiTableBodyCellProps: ({ row }: { row: any }) => ({
    sx: {
      backgroundColor: row.index % 2 === 0 ? C.rowEven : C.rowOdd,
      color: C.white,
      fontSize: "11px",
      fontFamily: '"Tactic Sans", sans-serif',
      borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
      borderRight: `1px solid ${GLASS_COLORS.borderLight}`,
      "& .MuiCheckbox-root": { color: C.white, "&.Mui-checked": { color: C.primary } },
      "& .MuiIconButton-root": {
        color: C.white,
        transition: "color 0.2s ease, background-color 0.2s ease",
        "&:hover": { color: C.primary, backgroundColor: "rgba(1, 102, 255, 0.15)" },
      },
    },
  }),

  muiTableBodyRowProps: ({ row }: { row: any }) => ({
    sx: {
      backgroundColor: row.index % 2 === 0 ? C.rowEven : C.rowOdd,
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
      backgroundColor: GLASS_COLORS.cardBg,
      border: `1px solid ${GLASS_COLORS.borderLight}`,
      borderRadius: "8px",
      "&::-webkit-scrollbar": { width: "8px", height: "8px" },
      "&::-webkit-scrollbar-track": { background: C.rowOdd },
      "&::-webkit-scrollbar-thumb": {
        backgroundColor: GLASS_COLORS.borderMedium,
        borderRadius: "4px",
      },
      "&::-webkit-scrollbar-thumb:hover": { backgroundColor: GLASS_COLORS.borderLight },
    },
  },

  muiTablePaperProps: {
    sx: {
      backgroundColor: GLASS_COLORS.cardBg,
      boxShadow: "none",
      border: `1px solid ${GLASS_COLORS.borderLight}`,
      borderRadius: "8px",
      overflow: "hidden",
    },
  },
};

/** Contenedor típico alrededor de `<MaterialReactTable />` (ancho flexible, sin overflow del padre). */
export const dataTableShellSx: SxProps<Theme> = {
  width: "100%",
  minWidth: 0,
  overflow: "hidden",
};

/** Mensaje de carga fuera de la tabla MRT (misma línea visual que Actuaciones). */
export const dataTableMrtLoadingMessageSx: SxProps<Theme> = {
  fontFamily: '"Tactic Sans", sans-serif',
  fontSize: "18px",
  color: DATA_TABLE_MRT_GLASS_COLORS.white,
  textAlign: "center",
  padding: "40px",
};
