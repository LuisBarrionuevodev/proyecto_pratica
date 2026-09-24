import { useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Paper, Tab, Tabs } from "@mui/material";

import {
  glassSecondaryTabsSx,
  glassTabsSecondaryPanelBarSx,
} from "../../styles/GlassStyles";

type EstablecimientosTab = "fichas" | "historial";

function tabFromPath(pathname: string): EstablecimientosTab {
  if (pathname.includes("/historial-contribuyente")) return "historial";
  return "fichas";
}

/**
 * Navegación superior del módulo Establecimientos (listado vs historial por documento).
 */
export function EstablecimientosModuleTabs() {
  const location = useLocation();
  const navigate = useNavigate();
  const current = useMemo(() => tabFromPath(location.pathname), [location.pathname]);

  return (
    <Paper elevation={0} sx={{ ...glassTabsSecondaryPanelBarSx, width: "100%" }}>
      <Tabs
        value={current}
        onChange={(_, value: EstablecimientosTab) => {
          if (value === "fichas") navigate("/establecimientos");
          else navigate("/establecimientos/historial-contribuyente");
        }}
        variant="scrollable"
        allowScrollButtonsMobile
        sx={glassSecondaryTabsSx}
      >
        <Tab label="Fichas operativas" value="fichas" />
        <Tab label="Historial por DNI/CUIT" value="historial" />
      </Tabs>
    </Paper>
  );
}
