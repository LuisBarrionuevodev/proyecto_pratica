import { Marker, Popup } from "react-leaflet";
import { FONT_FAMILY_UI } from "../../../theme/typography";

import { GLASS_COLORS } from "../../../styles/GlassStyles";
import type { PlanificacionUsedMarker } from "./utils/buildPlanificacionUsedMarkers";
import { planificacionUsedPinIcon } from "./utils/planificacionMapaPins";export type PlanificacionMapaUsedLayerProps = {
  markers: PlanificacionUsedMarker[];
};

/**
 * Capa de pines rojos para iniciadores ya agregados a la ruta (pool / grupo).
 * Siempre visible cuando hay markers (OPER-RUTA.FUNCIONAL-2A).
 */
export function PlanificacionMapaUsedLayer({ markers }: PlanificacionMapaUsedLayerProps) {
  return (
    <>
      {markers.map((m) => (
        <Marker key={`used-${m.iniciadorId}`} position={[m.lat, m.lng]} icon={planificacionUsedPinIcon()} zIndexOffset={500}>
          <Popup maxWidth={220} minWidth={180}>
            <div style={{ fontFamily: FONT_FAMILY_UI, fontSize: "0.75rem", color: GLASS_COLORS.textPrimary, lineHeight: 1.35 }}>
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
