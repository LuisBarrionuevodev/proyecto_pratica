import { Outlet } from "react-router-dom";
import { Box } from "@mui/material";

import { containerStyles } from "../CargarActuaciones/styles/cargarActuacionesStyles";

/**
 * Layout del módulo Establecimientos: outlet para listado y detalle.
 */
export default function EstablecimientosLayout() {
  return (
    <Box
      sx={{
        ...containerStyles,
        p: { xs: 1.5, sm: 2 },
        boxSizing: "border-box",
        minHeight: 0,
        width: "100%",
      }}
    >
      <Outlet />
    </Box>
  );
}
