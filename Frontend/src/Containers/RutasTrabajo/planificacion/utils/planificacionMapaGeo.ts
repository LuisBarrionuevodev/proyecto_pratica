import type { Feature, FeatureCollection } from "geojson";

/**
 * Centroide simple (promedio de vértices del anillo exterior) en [lat, lng].
 * Válido para polígonos de planificación; no es centro de masa real en cóncavos.
 */
export function centroidLatLngFromPolygonRings(rings: number[][][]): [number, number] | null {
  const outer = rings[0];
  if (!outer?.length) return null;
  const closed =
    outer.length > 1 &&
    outer[outer.length - 1][0] === outer[0][0] &&
    outer[outer.length - 1][1] === outer[0][1];
  const len = closed ? outer.length - 1 : outer.length;
  if (len < 1) return null;
  let lat = 0;
  let lng = 0;
  for (let i = 0; i < len; i++) {
    lng += outer[i][0];
    lat += outer[i][1];
  }
  return [lat / len, lng / len];
}

export function centroidLatLngForFeature(f: Feature): [number, number] | null {
  const g = f.geometry;
  if (!g || g.type === "GeometryCollection") return null;
  if (g.type === "Polygon") {
    return centroidLatLngFromPolygonRings(g.coordinates as number[][][]);
  }
  if (g.type === "MultiPolygon") {
    const polys = g.coordinates as number[][][][];
    if (polys[0]) return centroidLatLngFromPolygonRings(polys[0]);
  }
  return null;
}

export type DistritoMapLabel = {
  key: string;
  position: [number, number];
  cantidad: number;
};

export function buildDistritoMapLabels(geoData: FeatureCollection): DistritoMapLabel[] {
  const out: DistritoMapLabel[] = [];
  for (const f of geoData.features) {
    const p = f.properties as Record<string, unknown> | undefined;
    const rawId = p?.distrito_id;
    const id = typeof rawId === "number" ? rawId : rawId != null ? Number(rawId) : NaN;
    if (!Number.isFinite(id)) continue;
    const c = centroidLatLngForFeature(f);
    if (!c) continue;
    const cantidad = Number(p?.cantidad ?? 0);
    out.push({ key: `distrito-label-${id}`, position: c, cantidad });
  }
  return out;
}
