import L from "leaflet";

import type { PrioridadCat } from "./iniciadorDisplay";

const PIN_COLORS: Record<PrioridadCat, { fill: string; stroke: string }> = {
  BAJA: { fill: "#2e7d32", stroke: "#a5d6a7" },
  MEDIA: { fill: "#f9a825", stroke: "#fff59d" },
  ALTA: { fill: "#c62828", stroke: "#ffab91" },
};

/**
 * Icono tipo pin (SVG) coloreado por prioridad; `focused` agranda ligeramente el hit visual.
 */
export function planificacionPendientePinIcon(priority: PrioridadCat, focused: boolean): L.DivIcon {
  const { fill, stroke } = PIN_COLORS[priority] ?? PIN_COLORS.MEDIA;
  const w = focused ? 32 : 26;
  const h = focused ? 40 : 34;
  const scale = focused ? 1.12 : 1;
  const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 24 36" style="transform:scale(${scale});transform-origin:center bottom">
  <path d="M12 2C7.03 2 3 5.58 3 10.2c0 5.8 9 17.8 9 17.8s9-12 9-17.8C21 5.58 16.97 2 12 2z"
        fill="${fill}" stroke="${stroke}" stroke-width="1.4" stroke-linejoin="round"/>
  <circle cx="12" cy="10" r="3.2" fill="rgba(255,255,255,0.92)"/>
</svg>`.trim();

  return L.divIcon({
    className: "planif-leaflet-pin",
    html: svg,
    iconSize: [w, h],
    iconAnchor: [Math.round(w / 2), h],
    popupAnchor: [0, -h + 4],
  });
}

/** Pin redondo rojo para iniciadores ya agregados a la ruta (pool / grupo). */
export function planificacionUsedPinIcon(focused = false): L.DivIcon {
  const size = focused ? 18 : 14;
  const html = `<div style="
    width:${size}px;height:${size}px;border-radius:50%;
    background:#d32f2f;border:2px solid rgba(255,255,255,0.92);
    box-shadow:0 2px 6px rgba(0,0,0,0.45);
  "></div>`;
  return L.divIcon({
    className: "planif-leaflet-used-pin",
    html,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2 + 2)],
  });
}
