import { useMemo } from "react";
import { Marker, Pane } from "react-leaflet";
import type { FeatureCollection } from "geojson";
import L from "leaflet";

import { buildDistritoMapLabels } from "./utils/planificacionMapaGeo";

/** Celeste glass alineado a Digitaliza (#0166FF); legible sobre choropleta sin tapar clics. */
const DISTRITO_LABEL_INNER_STYLE =
  'font-size:42px;font-weight:800;line-height:1;text-align:center;pointer-events:none;user-select:none;min-width:1ch;' +
  'font-family:"Tactic Sans",sans-serif;color:#a8e8ff;opacity:0.68;' +
  "text-shadow:0 0 22px rgba(120,210,255,0.62),0 0 10px rgba(1,102,255,0.48),0 2px 12px rgba(0,0,0,0.55);";

function distritoLabelDivIcon(label: string): L.DivIcon {
  return L.divIcon({
    className: "planif-leaflet-distrito-num",
    html: `<div class="planif-distrito-num-inner" style="${DISTRITO_LABEL_INNER_STYLE}">${label}</div>`,
    iconSize: [88, 56],
    iconAnchor: [44, 28],
  });
}

type PlanificacionMapaDistritoLabelsLayerProps = {
  geoData: FeatureCollection;
};

/**
 * Código de distrito grande semitransparente (centroide del polígono).
 * Marcadores no interactivos para no bloquear clics en el GeoJSON de distritos.
 */
export function PlanificacionMapaDistritoLabelsLayer({ geoData }: PlanificacionMapaDistritoLabelsLayerProps) {
  const labels = useMemo(() => buildDistritoMapLabels(geoData), [geoData]);
  return (
    <Pane name="planif-distrito-labels" style={{ zIndex: 450 }}>
      {labels.map(({ key, position, label }) => (
        <Marker key={key} position={position} icon={distritoLabelDivIcon(label)} interactive={false} />
      ))}
    </Pane>
  );
}
