import { Paper, Tab, Tabs, Typography } from "@mui/material";

import type { MapaOperativoModo } from "../hooks/useMapaOperativo";
import { mapaOperativoGlassPanelSx } from "./mapaOperativoStyles";

export type MapaModoTabsProps = {
  modo: MapaOperativoModo;
  onModoChange: (m: MapaOperativoModo) => void;
};

/**
 * Selector de modo con el mismo patrón que CargarRelevamientos (Relevamientos / Denuncias): Tabs + tipografía auxiliar.
 */
export function MapaModoTabs({ modo, onModoChange }: MapaModoTabsProps) {
  return (
    <Paper elevation={0} sx={mapaOperativoGlassPanelSx}>
      <Typography variant="body2" sx={{ mb: 2, color: "rgba(255, 255, 255, 0.7)" }}>
        Pendientes y realizados en el territorio municipal
      </Typography>
      <Tabs value={modo} onChange={(_, value) => onModoChange(value as MapaOperativoModo)} sx={{ marginBottom: 0 }}>
        <Tab label="Pendientes" value="pendientes" />
        <Tab label="Realizados" value="realizados" />
      </Tabs>
    </Paper>
  );
}
