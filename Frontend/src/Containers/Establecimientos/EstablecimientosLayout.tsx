import { Outlet } from "react-router-dom";
import { Box } from "@mui/material";

import { functionalPageShellSx } from "../../styles/functionalPageShell";

/**
 * Layout del módulo Establecimientos: outlet para listado y detalle.
 */
export default function EstablecimientosLayout() {
  return (
    <Box sx={functionalPageShellSx}>
      <Outlet />
    </Box>
  );
}
