import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("OPER-RUTA.FUNCIONAL-2B.3A — cache compartida de iconos Leaflet", () => {
  const pins = read("Containers/RutasTrabajo/planificacion/utils/planificacionMapaPins.ts");
  const pendientesLayer = read("Containers/RutasTrabajo/planificacion/PlanificacionMapaPendientesLayer.tsx");
  const usedLayer = read("Containers/RutasTrabajo/planificacion/PlanificacionMapaUsedLayer.tsx");
  const mapa = read("Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");

  it("planificacionPendientePinIcon mantiene API y usa cache module-scoped", () => {
    expect(pins).toMatch(/export function planificacionPendientePinIcon\(priority: PrioridadCat, focused: boolean\)/);
    expect(pins).toContain("pendientePinIconCache");
    expect(pins).toMatch(/if \(cached\) return cached/);
    expect(pins).toContain('className: "planif-leaflet-pin"');
    expect(pins).toContain('fill: "#2e7d32"');
    expect(pins).toContain('fill: "#f9a825"');
    expect(pins).toContain('fill: "#c62828"');
  });

  it("planificacionUsedPinIcon usa cache", () => {
    expect(pins).toContain("usedPinIconCache");
    expect(pins).toMatch(/export function planificacionUsedPinIcon/);
  });

  it("PendientePlanifMarker sigue usando planificacionPendientePinIcon sin useMemo por icono", () => {
    expect(pendientesLayer).toMatch(/const icon = planificacionPendientePinIcon\(priority, isFocus\)/);
    expect(pendientesLayer).not.toMatch(/useMemo\(\(\) => planificacionPendientePinIcon/);
  });

  it("no se agregó clustering", () => {
    expect(mapa).not.toContain("MarkerCluster");
    expect(mapa).not.toContain("markercluster");
    expect(pendientesLayer).not.toContain("MarkerCluster");
    expect(pendientesLayer).not.toContain("markercluster");
  });

  it("used layer permanece separado de candidatos", () => {
    expect(mapa).toContain("PlanificacionMapaUsedLayer");
    expect(mapa).toContain('name="planif-used-pane"');
    expect(mapa).toContain('name="planif-pendientes-pane"');
    expect(usedLayer).toContain("planificacionUsedPinIcon");
  });
});
