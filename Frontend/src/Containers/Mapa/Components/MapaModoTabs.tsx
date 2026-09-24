import { Paper, Tab, Tabs } from "@mui/material";

import { moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../../styles/GlassStyles";

/** Modo de navegación en MapPage (PR6C.11). */
export type MapaModo = "geolocalizacion" | "realizados";

export type MapaModoTabsProps = {
  modo: MapaModo;
  onModoChange: (m: MapaModo) => void;
};

/**
 * Tabs principales Mapa — mismo patrón que RelevamientosSectionContainer (alineación izquierda, sin fullWidth).
 */
export function MapaModoTabs({ modo, onModoChange }: MapaModoTabsProps) {
  return (
    <Paper elevation={0} sx={moduleSlicesPanelPaperSx}>
      <Tabs value={modo} onChange={(_, value) => onModoChange(value as MapaModo)} sx={moduleSlicesTabsSx}>
        <Tab label="Geolocalización" value="geolocalizacion" />
        <Tab label="Realizados" value="realizados" />
      </Tabs>
    </Paper>
  );
}
