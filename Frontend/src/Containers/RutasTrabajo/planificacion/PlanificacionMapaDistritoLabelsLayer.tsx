import { useMemo } from "react";
import { Marker, Pane } from "react-leaflet";
import type { FeatureCollection } from "geojson";
import L from "leaflet";

import { buildDistritoMapLabels } from "./utils/planificacionMapaGeo";

function cantidadDivIcon(cantidad: number): L.DivIcon {
  return L.divIcon({
    className: "planif-leaflet-distrito-num",
    html: `<div class="planif-distrito-num-inner">${cantidad}</div>`,
    iconSize: [88, 56],
    iconAnchor: [44, 28],
  });
}

type PlanificacionMapaDistritoLabelsLayerProps = {
  geoData: FeatureCollection;
};

/**
 * Número grande semitransparente por distrito (centroide del polígono).
 * Marcadores no interactivos para no bloquear clics en el GeoJSON de distritos.
 */
export function PlanificacionMapaDistritoLabelsLayer({ geoData }: PlanificacionMapaDistritoLabelsLayerProps) {
  const labels = useMemo(() => buildDistritoMapLabels(geoData), [geoData]);
  return (
    <Pane name="planif-distrito-labels" style={{ zIndex: 450 }}>
      {labels.map(({ key, position, cantidad }) => (
        <Marker key={key} position={position} icon={cantidadDivIcon(cantidad)} interactive={false} />
      ))}
    </Pane>
  );
}
