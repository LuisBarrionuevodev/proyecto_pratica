import { Marker, Popup } from "react-leaflet";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import type { PlanificacionUsedMarker } from "./utils/buildPlanificacionUsedMarkers";
import { planificacionUsedPinIcon } from "./utils/planificacionMapaPins";

const tactic = '"Tactic Sans", sans-serif' as const;

export type PlanificacionMapaUsedLayerProps = {
  markers: PlanificacionUsedMarker[];
  visible?: boolean;
};

/**
 * Capa de pines rojos para iniciadores ya agregados a la ruta (pool / grupo).
 */
export function PlanificacionMapaUsedLayer({ markers, visible = true }: PlanificacionMapaUsedLayerProps) {
  if (!visible) return null;

  return (
    <>
      {markers.map((m) => (
        <Marker key={`used-${m.iniciadorId}`} position={[m.lat, m.lng]} icon={planificacionUsedPinIcon()} zIndexOffset={500}>
          <Popup maxWidth={220} minWidth={180}>
            <div style={{ fontFamily: tactic, fontSize: "0.75rem", color: GLASS_COLORS.textPrimary, lineHeight: 1.35 }}>
              <strong>
                {m.estado === "grupo" ? `En grupo: ${m.grupoNombre ?? "Grupo"}` : "En pool"}
              </strong>
              <div style={{ marginTop: 4 }}>{m.tipoLabel}</div>
              <div>{m.domicilio}</div>
              <div style={{ color: GLASS_COLORS.textMuted }}>{m.rubro}</div>
            </div>
          </Popup>
        </Marker>
      ))}
    </>
  );
}
