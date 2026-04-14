import { Paper, Tab, Tabs, Typography } from "@mui/material";

import { GLASS_COLORS, glassPrimaryTabsSx } from "../../../styles/GlassStyles";
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
      <Typography
        variant="body2"
        sx={{ mb: 2, color: GLASS_COLORS.textMuted, fontFamily: '"Tactic Sans", sans-serif' }}
      >
        Pendientes y realizados en el territorio municipal
      </Typography>
      <Tabs
        value={modo}
        onChange={(_, value) => onModoChange(value as MapaOperativoModo)}
        sx={glassPrimaryTabsSx}
      >
        <Tab label="Pendientes" value="pendientes" />
        <Tab label="Realizados" value="realizados" />
      </Tabs>
    </Paper>
  );
}
