import L from "leaflet";

import { COLORS } from "../../CargarActuaciones/styles/cargarActuacionesStyles";

const SHADOW = "0 2px 8px rgba(0,0,0,0.42)";

/**
 * Color de triángulo (cola planificable): misma categoría que backend (`prioridad_categoria`).
 * Lectura operativa: alta = rojo, media = naranja, baja = azul.
 */
export function colorPrioridadBacklog(prioridadCategoria: unknown): string {
  const c = String(prioridadCategoria ?? "").toUpperCase();
  if (c === "ALTA") return COLORS.error;
  if (c === "MEDIA") return COLORS.warning;
  return COLORS.primary;
}

/**
 * Icono semántico por feature (`map_layer` D1) y modo.
 * - iniciador_backlog: triángulo, color por prioridad
 * - ruta_en_proceso: cuadrado azul con «!» (solo ruta PUBLICADA + EN_PROCESO; sin borradores)
 * - ruta_realizado: pin clásico (visita realizada)
 */
export function createOperativoPointIcon(
  modo: "pendientes" | "realizados",
  properties: Record<string, unknown>
): L.DivIcon {
  const layer = String(properties.map_layer ?? "");

  if (layer === "ruta_realizado" || modo === "realizados") {
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

  if (layer === "ruta_en_proceso") {
    const bg = COLORS.primary;
    return L.divIcon({
      className: "mapa-op-en-proceso",
      html: `<div title="En ruta publicada · pendiente de completar trabajo" style="width:22px;height:22px;border-radius:4px;background:${bg};border:2px solid ${COLORS.white};box-shadow:${SHADOW};display:flex;align-items:center;justify-content:center;color:${COLORS.white};font-size:16px;line-height:1;font-weight:900;font-family:system-ui,sans-serif;">!</div>`,
      iconSize: [22, 22],
      iconAnchor: [11, 11],
      popupAnchor: [0, -10],
    });
  }

  /* iniciador_backlog o fallback en modo pendientes */
  const fill = colorPrioridadBacklog(properties.prioridad_categoria);
  const tri = `<div title="Iniciador en cola (planificable, aún no en ruta del día)" style="width:22px;height:20px;display:flex;justify-content:center;align-items:flex-end;"><div style="width:0;height:0;border-left:11px solid transparent;border-right:11px solid transparent;border-bottom:19px solid ${fill};filter:drop-shadow(0 2px 3px rgba(0,0,0,0.45));"></div></div>`;
  return L.divIcon({
    className: "mapa-op-backlog-tri",
    html: tri,
    iconSize: [22, 20],
    iconAnchor: [11, 19],
    popupAnchor: [0, -16],
  });
}
