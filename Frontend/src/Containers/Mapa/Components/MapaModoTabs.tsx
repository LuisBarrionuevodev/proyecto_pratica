import { Paper, Tab, Tabs } from "@mui/material";

import { moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../../styles/GlassStyles";

/** Modo de navegación en MapPage (PR6C.11). */
export type MapaModo = "geolocalizacion" | "realizados";

/** Modo Mi mapa (Inspector). */
export type MapaModoInspector = "trabajos" | "realizados";

export type MapaModoTabsProps = {
  modo: MapaModo;
  onModoChange: (m: MapaModo) => void;
  variant?: "global" | "inspector";
  modoInspector?: MapaModoInspector;
  onModoInspectorChange?: (m: MapaModoInspector) => void;
};

/**
 * Tabs principales Mapa — mismo patrón que RelevamientosSectionContainer (alineación izquierda, sin fullWidth).
 */
export function MapaModoTabs({
  modo,
  onModoChange,
  variant = "global",
  modoInspector = "trabajos",
  onModoInspectorChange,
}: MapaModoTabsProps) {
  if (variant === "inspector") {
    return (
      <Paper elevation={0} sx={moduleSlicesPanelPaperSx} data-testid="mapa-modo-tabs-inspector">
        <Tabs
          value={modoInspector}
          onChange={(_, value) => onModoInspectorChange?.(value as MapaModoInspector)}
          sx={moduleSlicesTabsSx}
        >
          <Tab label="Mis trabajos" value="trabajos" />
          <Tab label="Mis realizados" value="realizados" />
        </Tabs>
      </Paper>
    );
  }

  return (
    <Paper elevation={0} sx={moduleSlicesPanelPaperSx}>
      <Tabs value={modo} onChange={(_, value) => onModoChange(value as MapaModo)} sx={moduleSlicesTabsSx}>
        <Tab label="Geolocalización" value="geolocalizacion" />
        <Tab label="Realizados" value="realizados" />
      </Tabs>
    </Paper>
  );
}
