/**
 * Mini-mapa documental: imagen estática OSM (sin UI de Leaflet).
 * Evita captura de pantalla y depende solo de coordenadas del modelo de ruta.
 *
 * Servicio público con uso razonable; si falla CORS o red, el PDF sigue sin mapa.
 */

export type StaticMapParams = {
  width: number;
  height: number;
  /** Centro aproximado y zoom; marcadores opcionales acotados. */
  centerLat: number;
  centerLng: number;
  zoom: number;
  markers: { lat: number; lng: number }[];
  /**
   * Metadatos alineados con `markers` (misma longitud): grupo 1-based y orden en grupo.
   * El proxy con teselas colorea y dibuja **Gn** en cada pin; `pin_o` ordena la polilínea por grupo.
   */
  pinGrupo1Based?: number[];
  pinOrden?: number[];
};

const MAX_MARKERS = 18;

function clampZoom(z: number): number {
  return Math.min(18, Math.max(10, Math.round(z)));
}

/** 5 decimales (~1 m): URLs más cortas y alineadas con el proxy del backend. */
function roundCoord(n: number): number {
  return Math.round(n * 1e5) / 1e5;
}

/**
 * Estima zoom y centro a partir de puntos geográficos de la ruta.
 */
export function computeStaticMapView(points: { lat: number; lng: number }[]): Omit<StaticMapParams, "width" | "height"> | null {
  if (!points.length) return null;

  let minLat = points[0].lat;
  let maxLat = points[0].lat;
  let minLng = points[0].lng;
  let maxLng = points[0].lng;
  for (const p of points) {
    minLat = Math.min(minLat, p.lat);
    maxLat = Math.max(maxLat, p.lat);
    minLng = Math.min(minLng, p.lng);
    maxLng = Math.max(maxLng, p.lng);
  }

  const centerLat = (minLat + maxLat) / 2;
  const centerLng = (minLng + maxLng) / 2;
  const latSpan = Math.max(1e-6, maxLat - minLat);
  const lngSpan = Math.max(1e-6, maxLng - minLng);
  const cosLat = Math.cos((centerLat * Math.PI) / 180);
  const effLng = lngSpan * (cosLat < 0.2 ? 0.2 : cosLat);
  const span = Math.max(latSpan, effLng);

  let zoom = 14;
  if (span > 0.25) zoom = 11;
  else if (span > 0.12) zoom = 12;
  else if (span > 0.06) zoom = 13;
  else if (span > 0.03) zoom = 14;
  else zoom = 15;

  const markers = points.slice(0, MAX_MARKERS);
  return { centerLat, centerLng, zoom: clampZoom(zoom), markers };
}

/**
 * URL de imagen estática (OpenStreetMap staticmap).
 */
export function buildOsmStaticMapUrl(params: StaticMapParams): string {
  const { width, height, centerLat, centerLng, zoom, markers, pinGrupo1Based, pinOrden } = params;
  const base = "https://staticmap.openstreetmap.de/staticmap.php";
  const q = new URLSearchParams();
  q.set("center", `${roundCoord(centerLat)},${roundCoord(centerLng)}`);
  q.set("zoom", String(zoom));
  q.set("size", `${width}x${height}`);
  q.set("maptype", "mapnik");

  if (markers.length) {
    const part = markers.map((m) => `${roundCoord(m.lat)},${roundCoord(m.lng)},red-pushpin`).join("|");
    q.set("markers", part);
    const n = markers.length;
    if (
      pinGrupo1Based &&
      pinOrden &&
      pinGrupo1Based.length === n &&
      pinOrden.length === n
    ) {
      q.set("pin_g", pinGrupo1Based.join("|"));
      q.set("pin_o", pinOrden.join("|"));
    }
  }

  return `${base}?${q.toString()}`;
}

/**
 * Descarga la imagen y la convierte a data URL para embeber en @react-pdf/renderer.
 * @returns data URL o null si no se pudo obtener.
 */
async function blobToDataUrl(blob: Blob): Promise<string | null> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onerror = () => resolve(null);
    reader.onloadend = () => resolve(typeof reader.result === "string" ? reader.result : null);
    reader.readAsDataURL(blob);
  });
}

export type FetchStaticMapOptions = {
  /**
   * URL absoluta al proxy del backend (misma query que OSM, p. ej. …/map/osm-static?center=…).
   * Evita CORS: el navegador llama al API con JWT y el servidor obtiene la imagen de OSM.
   */
  proxyAbsoluteUrl?: string | null;
  /** Headers extra para el proxy (p. ej. Authorization Bearer). */
  proxyFetchInit?: RequestInit;
  /** Misma semántica que en `buildOsmStaticMapUrl` (colores / Gn en el pin vía proxy teselas). */
  pinGrupo1Based?: number[];
  pinOrden?: number[];
};

/**
 * Descarga la imagen y la convierte a data URL para embeber en @react-pdf/renderer.
 * Si se indica `proxyAbsoluteUrl`, se intenta primero el proxy y luego OSM directo.
 *
 * @returns data URL o null si no se pudo obtener.
 */
export async function fetchStaticMapAsDataUrl(
  view: Omit<StaticMapParams, "width" | "height">,
  size: { width: number; height: number },
  options?: FetchStaticMapOptions
): Promise<string | null> {
  const nPins = view.markers.length;
  const pinsOk =
    options?.pinGrupo1Based &&
    options?.pinOrden &&
    options.pinGrupo1Based.length === nPins &&
    options.pinOrden.length === nPins;
  const pinExtra = pinsOk
    ? { pinGrupo1Based: options.pinGrupo1Based, pinOrden: options.pinOrden }
    : {};
  const directUrl = buildOsmStaticMapUrl({ ...view, ...size, ...pinExtra });

  const tryOnce = async (url: string, init?: RequestInit): Promise<string | null> => {
    try {
      const res = await fetch(url, { mode: "cors", ...init });
      if (!res.ok) return null;
      const blob = await res.blob();
      return blobToDataUrl(blob);
    } catch {
      return null;
    }
  };

  const proxy = options?.proxyAbsoluteUrl?.trim();
  if (proxy) {
    const viaProxy = await tryOnce(proxy, options.proxyFetchInit);
    if (viaProxy) return viaProxy;
  }

  return tryOnce(directUrl);
}
