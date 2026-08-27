import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("OPER-RUTA.FUNCIONAL-2B.2 — GeoJSON estable al cambiar distrito", () => {
  const mapa = read("Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");
  const pendientesLayer = read("Containers/RutasTrabajo/planificacion/PlanificacionMapaPendientesLayer.tsx");
  const usedLayer = read("Containers/RutasTrabajo/planificacion/PlanificacionMapaUsedLayer.tsx");

  it("caso A — MapContainer estable sin key dependiente de distrito", () => {
    expect(mapa).toContain("<MapContainer");
    expect(mapa).not.toMatch(/<MapContainer[^>]*\bkey=/);
  });

  it("caso B — GeoJSON key sin distritoActivoId", () => {
    expect(mapa).toContain("geoJsonKey");
    expect(mapa).not.toContain("mapKey");
    expect(mapa).toMatch(/const geoJsonKey = `\$\{geoData\.features\.length\}-\$\{distritoCatalogo\.length\}`/);
    const geoJsonKeyLine = mapa.match(/const geoJsonKey =[^\n]+/)?.[0] ?? "";
    expect(geoJsonKeyLine).not.toContain("distritoActivoId");
    expect(mapa).toMatch(/<GeoJSON[\s\S]*?key=\{geoJsonKey\}/);
  });

  it("caso C — selección sigue afectando styleFn", () => {
    expect(mapa).toMatch(/const styleFn[\s\S]*distritoActivoId/);
    expect(mapa).toMatch(/selected = id != null && id === distritoActivoId/);
  });

  it("caso D — key depende de señales estructurales del GeoJSON/catálogo", () => {
    expect(mapa).toContain("geoData.features.length");
    expect(mapa).toContain("distritoCatalogo.length");
    expect(mapa).not.toMatch(/JSON\.stringify\(geoData/);
  });

  it("caso E — used markers intactos", () => {
    expect(usedLayer).toContain('key={`used-${m.iniciadorId}`}');
    expect(mapa).toContain("PlanificacionMapaUsedLayer");
  });

  it("caso F — candidatos siguen condicionados por distrito activo", () => {
    expect(mapa).toMatch(/PlanificacionMapaPendientesLayer[\s\S]*visible=\{distritoActivoId != null\}/);
    expect(pendientesLayer).toContain("if (!visible) return null");
  });

  it("no agrega efecto imperativo setStyle en esta fase", () => {
    expect(mapa).not.toContain("useMap");
    expect(mapa).not.toContain("setStyle(");
    expect(mapa).not.toContain("layerRef");
  });
});
