import { describe, expect, it, vi } from "vitest";

vi.mock("leaflet", () => ({
  default: {
    divIcon: (options: Record<string, unknown>) => ({ options }),
  },
}));

import type { PrioridadCat } from "./iniciadorDisplay";
import { planificacionPendientePinIcon, planificacionUsedPinIcon } from "./planificacionMapaPins";

const PRIORIDADES: PrioridadCat[] = ["BAJA", "MEDIA", "ALTA"];

describe("planificacionMapaPins — cache 2B.3A", () => {
  it("A — misma variante devuelve la misma instancia L.DivIcon", () => {
    const a = planificacionPendientePinIcon("BAJA", false);
    const b = planificacionPendientePinIcon("BAJA", false);
    expect(a).toBe(b);
  });

  it("B — focus produce instancia distinta", () => {
    const normal = planificacionPendientePinIcon("ALTA", false);
    const focused = planificacionPendientePinIcon("ALTA", true);
    expect(normal).not.toBe(focused);
  });

  it("C — prioridades distintas producen instancias distintas", () => {
    const baja = planificacionPendientePinIcon("BAJA", false);
    const media = planificacionPendientePinIcon("MEDIA", false);
    expect(baja).not.toBe(media);
  });

  it("D — las 6 combinaciones reutilizan como máximo 6 instancias candidatas", () => {
    const instances = new Set<ReturnType<typeof planificacionPendientePinIcon>>();
    for (const priority of PRIORIDADES) {
      for (const focused of [false, true] as const) {
        instances.add(planificacionPendientePinIcon(priority, focused));
        instances.add(planificacionPendientePinIcon(priority, focused));
      }
    }
    expect(instances.size).toBe(6);
  });

  it("E — SVG/HTML y opciones del icono permanecen intactos", () => {
    const icon = planificacionPendientePinIcon("MEDIA", false);
    expect(icon.options.className).toBe("planif-leaflet-pin");
    expect(icon.options.iconSize).toEqual([26, 34]);
    expect(icon.options.iconAnchor).toEqual([13, 34]);
    expect(icon.options.popupAnchor).toEqual([0, -30]);
    const html = String(icon.options.html ?? "");
    expect(html).toContain('fill="#f9a825"');
    expect(html).toContain('stroke="#fff59d"');
    expect(html).toContain('width="26"');
    expect(html).toContain('height="34"');
  });

  it("E — variante focused conserva tamaños esperados", () => {
    const icon = planificacionPendientePinIcon("ALTA", true);
    expect(icon.options.iconSize).toEqual([32, 40]);
    expect(icon.options.iconAnchor).toEqual([16, 40]);
    expect(icon.options.popupAnchor).toEqual([0, -36]);
    const html = String(icon.options.html ?? "");
    expect(html).toContain('fill="#c62828"');
    expect(html).toContain('width="32"');
    expect(html).toContain("transform:scale(1.12)");
  });

  it("F — used pin reutiliza instancia", () => {
    const a = planificacionUsedPinIcon();
    const b = planificacionUsedPinIcon();
    expect(a).toBe(b);
    expect(a.options.className).toBe("planif-leaflet-used-pin");
    expect(a.options.iconSize).toEqual([14, 14]);
  });

  it("F — used pin focused es instancia distinta", () => {
    const normal = planificacionUsedPinIcon(false);
    const focused = planificacionUsedPinIcon(true);
    expect(normal).not.toBe(focused);
    expect(focused.options.iconSize).toEqual([18, 18]);
  });
});
