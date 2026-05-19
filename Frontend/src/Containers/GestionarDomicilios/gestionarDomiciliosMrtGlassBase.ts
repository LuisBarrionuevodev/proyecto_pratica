import type { MRT_TableOptions } from "material-react-table";

import { BANDEJA_MRT_BODY_CELL_PROPS } from "../Actuaciones/Components/bandejaTableCells";
import { DARK_TABLE_CONFIG } from "../Actuaciones/styles/actuacionesTableStyles";

/**
 * Base visual MRT para Gestión de domicilios (F3.7c / F3.10): preset Actuaciones + bandeja 12px/600
 * + toolbar apilable en viewport angosto.
 */
export const GESTION_DOMICILIOS_MRT_GLASS_BASE: Partial<MRT_TableOptions<any>> = {
  ...DARK_TABLE_CONFIG,
  ...BANDEJA_MRT_BODY_CELL_PROPS,
  muiTopToolbarProps: {
    sx: {
      ...((DARK_TABLE_CONFIG.muiTopToolbarProps as { sx?: Record<string, unknown> })?.sx ?? {}),
      flexDirection: { xs: "column", md: "row" },
    },
  },
};
