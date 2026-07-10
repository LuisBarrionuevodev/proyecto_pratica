import L from "leaflet";

import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";

/**
 * Icono pin verde para visitas realizadas (`map_layer: ruta_realizado`).
 */
export function createOperativoPointIcon(_properties: Record<string, unknown>): L.DivIcon {
  const fill = COLORS.success;
  const stroke = COLORS.white;
  const svg = `<svg width="28" height="34" viewBox="0 0 28 34" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M14 2C8 2 3 6.8 3 12.8c0 6.5 9.2 17.4 10.6 19 .2.3.5.5.9.5.4 0 .7-.2.9-.5 1.4-1.6 10.6-12.5 10.6-19C26 6.8 21 2 14 2z" fill="${fill}" stroke="${stroke}" stroke-width="2"/><circle cx="14" cy="12" r="4" fill="${stroke}" fill-opacity="0.95"/></svg>`;
  return L.divIcon({
    className: "mapa-op-realizado-pin",
    html: `<div style="display:flex;justify-content:center;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.35));">${svg}</div>`,
    iconSize: [28, 34],
    iconAnchor: [14, 32],
    popupAnchor: [0, -28],
  });
}
