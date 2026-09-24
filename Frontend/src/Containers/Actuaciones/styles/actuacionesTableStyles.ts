import type { MRT_TableOptions } from "material-react-table";
import type { SxProps, Theme } from "@mui/material";

import {
  DATA_TABLE_MRT_GLASS_COLORS,
  dataTableMrtLoadingMessageSx,
  MRT_DATA_TABLE_GLASS_PRESET,
} from "../../../styles/mrtGlassDataTablePreset";

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
// Preset visual compartido: `styles/mrtGlassDataTablePreset.ts` (F3.7b).
// =============================================================================

/** @deprecated Preferir importar `DATA_TABLE_MRT_GLASS_COLORS` desde `styles/mrtGlassDataTablePreset` en código nuevo. */
export const COLORS = DATA_TABLE_MRT_GLASS_COLORS;

/**
 * Defaults preset glass compartidos; `TablaActuaciones` fuerza localmente sin selección (G1c-hotfix).
 * Otras pantallas suelen hacer `...MRT_DATA_TABLE_GLASS_PRESET` y sobrescriben solo lo necesario.
 */
export const DARK_TABLE_CONFIG: Partial<MRT_TableOptions<any>> = {
  ...MRT_DATA_TABLE_GLASS_PRESET,
  enableEditing: true,
  editDisplayMode: "cell" as const,
  enableSelectAll: true,
  enableRowSelection: true,
  enableColumnFilters: true,
  enableGlobalFilter: true,
  enablePagination: true,
  enableSorting: true,
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

export const loadingStyles: SxProps<Theme> = dataTableMrtLoadingMessageSx;

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
