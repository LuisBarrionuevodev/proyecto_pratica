import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");

function read(rel: string): string {
  return readFileSync(resolve(root, rel), "utf8");
}

describe("OPER-RUTA.FUNCIONAL-2B.3B — memo PendientePlanifMarker", () => {
  const layer = read("Containers/RutasTrabajo/planificacion/PlanificacionMapaPendientesLayer.tsx");
  const compare = read("Containers/RutasTrabajo/planificacion/utils/planificacionPendienteMarkerCompare.ts");
  const pins = read("Containers/RutasTrabajo/planificacion/utils/planificacionMapaPins.ts");
  const mapa = read("Containers/RutasTrabajo/planificacion/PlanificacionMapaDistritos.tsx");

  it("PendientePlanifMarker está memoizado con comparator custom", () => {
    expect(layer).toMatch(/const PendientePlanifMarker = memo\(function PendientePlanifMarker/);
    expect(layer).toContain("pendientePlanifMarkerAreEqual");
    expect(layer).toContain("arePendienteMarkerPropsEqual");
    expect(compare).toContain("export function arePendienteMarkerPropsEqual");
  });

  it("priority explícita desde layer y cache 2B.3A en icono", () => {
    expect(layer).toContain("priority={prioridadCategoriaRow(row)}");
    expect(layer).toMatch(/const icon = planificacionPendientePinIcon\(priority, isFocus\)/);
    expect(layer).not.toMatch(/useMemo\(\(\) => planificacionPendientePinIcon/);
    expect(pins).toContain("pendientePinIconCache");
  });

  it("eventHandlers de click estables con rowRef (sin stale)", () => {
    expect(layer).toContain("rowRef.current = row");
    expect(layer).toContain("onMarkerClickRef.current = onMarkerClick");
    expect(layer).toMatch(/markerClickHandlers = useMemo/);
    expect(layer).toMatch(/click: \(\) => onMarkerClickRef\.current\(rowRef\.current\)/);
    expect(layer).not.toMatch(/eventHandlers=\{\{\s*click: \(\) => onMarkerClick\(row\)/);
  });

  it("popup solo cuando showPopup y rowSignature en props", () => {
    expect(layer).toMatch(/\{showPopup \? \(\s*<Popup/);
    expect(layer).toContain("rowSignature={pendienteMarkerRowSignature(row)}");
    expect(layer).toContain('key={row.id}');
  });

  it("no se agregó clustering ni memo al layer completo", () => {
    expect(mapa).not.toContain("MarkerCluster");
    expect(layer).not.toMatch(/memo\(function PlanificacionMapaPendientesLayer/);
    expect(layer).not.toMatch(/export function PlanificacionMapaPendientesLayer = memo/);
  });
});
