import { Paper, Tab, Tabs } from "@mui/material";

import { moduleSlicesPanelPaperSx, moduleSlicesTabsSx } from "../../../styles/GlassStyles";
import type { MapaOperativoModo } from "../hooks/useMapaOperativo";

const tactic = '"Tactic Sans", sans-serif' as const;

export type MapaModoTabsProps = {
  modo: MapaOperativoModo;
  onModoChange: (m: MapaOperativoModo) => void;
};

/**
 * Slice de modo: mismo Paper + Tabs secundarios que Actas de comprobación / Relevamientos (F3.8c).
 */
export function MapaModoTabs({ modo, onModoChange }: MapaModoTabsProps) {
  return (
    <Paper elevation={0} sx={moduleSlicesPanelPaperSx}>
      <Tabs
        value={modo}
        onChange={(_, value) => onModoChange(value as MapaOperativoModo)}
        variant="fullWidth"
        sx={{ ...moduleSlicesTabsSx, width: "100%" }}
      >
        <Tab label="Pendientes" value="pendientes" sx={{ fontFamily: tactic, fontWeight: 500, textTransform: "none" }} />
        <Tab label="Realizados" value="realizados" sx={{ fontFamily: tactic, fontWeight: 500, textTransform: "none" }} />
      </Tabs>
    </Paper>
  );
}
