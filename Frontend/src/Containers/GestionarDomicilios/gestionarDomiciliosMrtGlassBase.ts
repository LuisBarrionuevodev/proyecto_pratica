import type { MRT_TableOptions } from "material-react-table";

import { MRT_DATA_TABLE_GLASS_PRESET } from "../../styles/mrtGlassDataTablePreset";

/**
 * Base visual MRT para Gestión de domicilios (F3.7c): preset glass institucional + toolbar
 * apilable en viewport angosto (comportamiento previo de `TablePendientesStyle`).
 * Las tablas del módulo hacen spread y añaden solo flags/edit/display propios.
 */
export const GESTION_DOMICILIOS_MRT_GLASS_BASE: Partial<MRT_TableOptions<any>> = {
  ...MRT_DATA_TABLE_GLASS_PRESET,
  muiTopToolbarProps: {
    sx: {
      ...((MRT_DATA_TABLE_GLASS_PRESET.muiTopToolbarProps as { sx?: Record<string, unknown> })?.sx ??
        {}),
      flexDirection: { xs: "column", md: "row" },
    },
  },
};
