import type { FeatureCollection } from "geojson";

import type { DistritoCatalogoItem } from "../../../../api/geolocalizacionApi";
import type { ICargaDistritoRow } from "../types/planificacion.types";

function norm(s: string): string {
  return s.trim().toLowerCase();
}

/**
 * Enriquece el GeoJSON de polígonos con `distrito_id` y `distrito_nombre` **canónicos** desde el catálogo DB
 * (`/geolocalizacion/distritos/catalogo`) y con `cantidad` desde M2 (por `distrito_id`).
 *
 * Fallback temporal: si el nombre del polígono no está en catálogo pero sí en M2, usa el id de M2.
 */
export function enrichPlanificacionDistritosGeoJson(
  base: FeatureCollection,
  catalog: DistritoCatalogoItem[],
  cargaPorDistrito: ICargaDistritoRow[]
): FeatureCollection {
  const byNombreCatalog = new Map<string, DistritoCatalogoItem>();
  catalog.forEach((c) => byNombreCatalog.set(norm(c.nombre), c));

  const cantidadByDistritoId = new Map<number, number>();
  const idByNombreCarga = new Map<string, number>();
  cargaPorDistrito.forEach((r) => {
    cantidadByDistritoId.set(r.distrito_id, r.cantidad);
    idByNombreCarga.set(norm(r.distrito_nombre), r.distrito_id);
  });

  return {
    ...base,
    features: base.features.map((f) => {
      const props = (f.properties ?? {}) as Record<string, unknown>;
      const nombrePoly = String(props.nombre ?? "");
      const key = norm(nombrePoly);

      let distrito_id: number | null = null;
      let distrito_nombre: string | null = null;

      const cat = byNombreCatalog.get(key);
      if (cat) {
        distrito_id = cat.id;
        distrito_nombre = cat.nombre;
      } else {
        const idFromCarga = idByNombreCarga.get(key);
        if (idFromCarga != null) {
          distrito_id = idFromCarga;
          distrito_nombre =
            cargaPorDistrito.find((x) => x.distrito_id === idFromCarga)?.distrito_nombre ?? nombrePoly;
        }
      }

      const cantidad =
        distrito_id != null ? cantidadByDistritoId.get(distrito_id) ?? 0 : 0;

      return {
        ...f,
        properties: {
          ...props,
          distrito_id,
          distrito_nombre,
          cantidad,
        },
      };
    }),
  };
}
