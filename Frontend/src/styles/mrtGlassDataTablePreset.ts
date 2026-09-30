import type { SxProps, Theme } from "@mui/material";
import type { MRT_TableOptions } from "material-react-table";

import { GLASS_COLORS } from "./GlassStyles";
import { CSS_VAR_NAMES as V } from "../theme/applyCssVariables";
import { FONT_FAMILY_UI } from "../theme/typography";

/**
 * Paleta compartida para tablas MRT — referencias CSS dinámicas (FRONT-PROD.3).
 * Claves históricas (`white`, `black`) conservadas por compatibilidad de imports.
 */
export const DATA_TABLE_MRT_GLASS_COLORS = {
  primary: `var(${V.actionPrimary})`,
  black: `var(${V.primitiveBlack})`,
  white: `var(${V.textPrimary})`,
  grayDark: `var(${V.tableRowEven})`,
  grayMedium: `var(${V.borderStrong})`,
  grayLight: `var(${V.surfaceInput})`,
  grayLighter: `var(${V.surfacePanelElevated})`,
  success: `var(${V.statusSuccess})`,
  successLight: `var(${V.statusSuccess})`,
  error: `var(${V.statusError})`,
  errorLight: `var(${V.statusError})`,
  warning: `var(${V.statusWarning})`,
  warningLight: `var(${V.statusWarning})`,
  rowEven: `var(${V.tableRowEven})`,
  rowOdd: `var(${V.tableRowOdd})`,
  border: `var(${V.borderStrong})`,
};

/** Valores string (evita literales `as const` de dark al asignar fondos de celda Glide). */
export type DataTableMrtGlassColors = {
  [K in keyof typeof DATA_TABLE_MRT_GLASS_COLORS]: string;
};

const C = DATA_TABLE_MRT_GLASS_COLORS;

/** Fuente de producto para tablas MRT (Actuaciones / bandejas). */
export const MRT_UI_FONT_FAMILY = FONT_FAMILY_UI;

/** @deprecated Use MRT_UI_FONT_FAMILY */
export const MRT_TACTIC_FONT_FAMILY = MRT_UI_FONT_FAMILY;

/** Tipografía header MRT — referencia Actuaciones (computed: 12px / 600). */
export const mrtActuacionesHeadCellTypographySx: SxProps<Theme> = {
  fontFamily: MRT_UI_FONT_FAMILY,
  fontSize: "12px",
  fontWeight: 600,
  lineHeight: 1.43,
  letterSpacing: "normal",
  textTransform: "none",
};

/** Tipografía body MRT — referencia Actas Comprobación / bandeja (12px / 600). */
export const mrtActuacionesBodyCellTypographySx: SxProps<Theme> = {
  fontFamily: MRT_UI_FONT_FAMILY,
  fontSize: "12px",
  fontWeight: 600,
  lineHeight: 1.35,
  letterSpacing: "normal",
  textTransform: "none",
};

/**
 * Scope tipográfico fuerte para tablas MRT (F3.10).
 * Aplica fuente/tamaño vía selectores descendientes cuando MRT/MUI pisan `muiTable*CellProps`.
 */
export const dataTableMrtTypographyScopeSx: SxProps<Theme> = {
  fontFamily: MRT_UI_FONT_FAMILY,
  "& .MuiTableCell-head": mrtActuacionesHeadCellTypographySx,
  "& .MuiTableCell-body": mrtActuacionesBodyCellTypographySx,
  "& .MuiTableCell-root": {
    fontFamily: MRT_UI_FONT_FAMILY,
  },
  "& .MuiTableCell-root .MuiTypography-root": {
    fontFamily: "inherit",
    fontSize: "inherit",
    fontWeight: "inherit",
    lineHeight: "inherit",
    letterSpacing: "inherit",
    textTransform: "inherit",
  },
  "& .MuiTablePagination-root, & .MuiTablePagination-toolbar, & .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows, & .MuiTablePagination-select, & .MuiTablePagination-input":
    {
      fontFamily: MRT_UI_FONT_FAMILY,
      fontSize: "12px",
      fontWeight: 400,
      letterSpacing: "normal",
      textTransform: "none",
    },
  "& .MuiToolbar-root": {
    fontFamily: MRT_UI_FONT_FAMILY,
    fontSize: "12px",
    fontWeight: 400,
  },
  "& .MuiInputBase-root, & .MuiInputBase-input, & .MuiInputLabel-root": {
    fontFamily: MRT_UI_FONT_FAMILY,
    fontSize: "12px",
  },
  "& .MuiChip-label": {
    fontFamily: MRT_UI_FONT_FAMILY,
    fontSize: "0.78rem",
    fontWeight: 600,
    letterSpacing: "normal",
    textTransform: "none",
  },
  "& .MuiButton-root": {
    fontFamily: MRT_UI_FONT_FAMILY,
    textTransform: "none",
  },
};

type MrtBodyCellCtx = { row: { index: number; original?: unknown }; column: { id?: string } };

/**
 * Compone `muiTableBodyCellProps` del preset con parches locales (p. ej. highlight de error).
 * Evita reemplazar el preset y perder tipografía/zebra (bug Relevamientos F3.10).
 */
export function mergeMrtBodyCellPropsWithActuacionesPreset(
  baseProp: MRT_TableOptions<any>["muiTableBodyCellProps"],
  patch?: (ctx: MrtBodyCellCtx) => { sx?: Record<string, unknown> } | void
): NonNullable<MRT_TableOptions<any>["muiTableBodyCellProps"]> {
  return (ctx) => {
    const baseResolved =
      typeof baseProp === "function"
        ? baseProp(ctx as Parameters<Extract<typeof baseProp, Function>>[0])
        : baseProp ?? {};
    const baseSx = ((baseResolved as { sx?: Record<string, unknown> }).sx ?? {}) as Record<
      string,
      unknown
    >;
    const merged = {
      ...baseResolved,
      sx: {
        ...mrtActuacionesBodyCellTypographySx,
        ...baseSx,
      },
    };
    const patchResult = patch?.(ctx as MrtBodyCellCtx);
    if (patchResult?.sx) {
      merged.sx = { ...(merged.sx as Record<string, unknown>), ...patchResult.sx };
    }
    return merged;
  };
}

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
      fontFamily: MRT_UI_FONT_FAMILY,
      fontSize: "12px",
      "& .MuiIconButton-root": {
        color: C.white,
        transition: "color 0.2s ease",
        "&:hover": { color: C.primary, backgroundColor: `var(${V.actionPrimaryMuted})` },
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
      fontFamily: MRT_UI_FONT_FAMILY,
      fontSize: "12px",
      "& .MuiTablePagination-root": { color: C.white },
      "& .MuiIconButton-root": {
        color: C.white,
        transition: "color 0.2s ease, background-color 0.2s ease",
        "&:hover": { color: C.primary, backgroundColor: `var(${V.actionPrimaryMuted})` },
        "&.Mui-disabled": { color: GLASS_COLORS.textMuted },
      },
      "& .MuiSelect-select": { color: C.white },
      "& .MuiSelect-icon": { color: C.white },
    },
  },

  muiTableHeadCellProps: {
    sx: {
      backgroundColor: `var(${V.surfaceTableHeader})`,
      color: C.white,
      ...mrtActuacionesHeadCellTypographySx,
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
        "&:hover": { color: C.primary, backgroundColor: `var(${V.actionPrimaryMuted})` },
      },
    },
  },

  muiTableBodyCellProps: ({ row }: { row: any }) => ({
    sx: {
      backgroundColor: row.index % 2 === 0 ? C.rowEven : C.rowOdd,
      color: C.white,
      ...mrtActuacionesBodyCellTypographySx,
      borderBottom: `1px solid ${GLASS_COLORS.borderLight}`,
      borderRight: `1px solid ${GLASS_COLORS.borderLight}`,
      "& .MuiCheckbox-root": { color: C.white, "&.Mui-checked": { color: C.primary } },
      "& .MuiIconButton-root": {
        color: C.white,
        transition: "color 0.2s ease, background-color 0.2s ease",
        "&:hover": { color: C.primary, backgroundColor: `var(${V.actionPrimaryMuted})` },
      },
    },
  }),

  muiTableBodyRowProps: ({ row }: { row: any }) => ({
    sx: {
      backgroundColor: row.index % 2 === 0 ? C.rowEven : C.rowOdd,
      "&:hover": { backgroundColor: `var(${V.tableRowHover})` },
      "&.Mui-selected": {
        backgroundColor: `var(${V.tableRowSelected})`,
        "&:hover": { backgroundColor: `var(${V.tableRowSelectedHover})` },
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
      backgroundColor: C.rowEven,
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
      ...dataTableMrtTypographyScopeSx,
    },
  },
};

/** Contenedor típico alrededor de `<MaterialReactTable />` (ancho flexible, sin overflow del padre). */
export const dataTableShellSx: SxProps<Theme> = {
  width: "100%",
  minWidth: 0,
  overflow: "hidden",
};

/** Overlay semitransparente sobre la tabla durante carga (F3.10). */
export const dataTableMrtLoadingOverlaySx: SxProps<Theme> = {
  position: "absolute",
  inset: 0,
  zIndex: 2,
  bgcolor: `var(${V.surfaceOverlay})`,
  display: "flex",
  flexDirection: "column",
  justifyContent: "center",
  alignItems: "center",
  gap: 1,
  borderRadius: "8px",
  pointerEvents: "none",
};

/** Texto bajo el spinner del overlay de tablas MRT. */
export const dataTableMrtLoadingOverlayMessageSx: SxProps<Theme> = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "0.8125rem",
  color: `var(${V.textSecondary})`,
};

/** Opacidad suave de la tabla mientras carga (prerender sin desmontar). */
export const dataTableMrtContentWhileLoadingSx: SxProps<Theme> = {
  opacity: 0.65,
  transition: "opacity 0.22s ease",
};

export const dataTableMrtContentReadySx: SxProps<Theme> = {
  opacity: 1,
  transition: "opacity 0.22s ease",
};

/** Mensaje de carga fuera de la tabla MRT (misma línea visual que Actuaciones). */
export const dataTableMrtLoadingMessageSx: SxProps<Theme> = {
  fontFamily: FONT_FAMILY_UI,
  fontSize: "18px",
  color: DATA_TABLE_MRT_GLASS_COLORS.white,
  textAlign: "center",
  padding: "40px",
};
