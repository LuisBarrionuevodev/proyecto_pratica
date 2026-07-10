import type { MRT_TableOptions } from "material-react-table";

import { BANDEJA_MRT_BODY_CELL_PROPS } from "../../../Actuaciones/Components/bandejaTableCells";
import { DARK_TABLE_CONFIG } from "../../../Actuaciones/styles/actuacionesTableStyles";

/** Base visual MRT para geolocalización domicilios — tabla limpia sin toolbar interna (PR6C.7). */
export const GESTION_DOMICILIOS_MRT_GLASS_BASE: Partial<MRT_TableOptions<any>> = {
  ...DARK_TABLE_CONFIG,
  ...BANDEJA_MRT_BODY_CELL_PROPS,
  enableTopToolbar: false,
  enableGlobalFilter: false,
  enableColumnFilters: false,
  enableHiding: false,
  enableDensityToggle: false,
  enableFullScreenToggle: false,
  enableColumnOrdering: false,
  enableSorting: false,
};
