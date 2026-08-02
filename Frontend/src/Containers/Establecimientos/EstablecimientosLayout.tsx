import { Outlet, useLocation } from "react-router-dom";
import { Box } from "@mui/material";

import { functionalPageShellSx } from "../../styles/functionalPageShell";
import { EstablecimientosModuleTabs } from "./EstablecimientosModuleTabs";

/**
 * Layout del módulo Establecimientos: tabs de sección + outlet para listado, historial y detalle.
 */
export default function EstablecimientosLayout() {
  const location = useLocation();
  const showModuleTabs = !/^\/establecimientos\/\d+$/.test(location.pathname);

  return (
    <Box sx={functionalPageShellSx}>
      {showModuleTabs ? <EstablecimientosModuleTabs /> : null}
      <Outlet />
    </Box>
  );
}
