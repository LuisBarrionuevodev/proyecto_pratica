import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { getVisibleHomeCards, getVisibleMenuSections } from "../auth/accessConfig";
import { resolveBreadcrumbLabel } from "./breadcrumbLabel";
import {
  isMenuPathVisibleForRole,
  isPathAllowedForRole,
  mapaLabelForRole,
} from "../auth/roles";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("V1.1-INSPECTOR.6 — Mi mapa", () => {
  it("relevador accede a /mapa con rótulo Mi mapa", () => {
    expect(isPathAllowedForRole("relevador", "/mapa")).toBe(true);
    expect(isMenuPathVisibleForRole("relevador", "/mapa")).toBe(true);
    expect(mapaLabelForRole("relevador")).toBe("Mi mapa");
    expect(mapaLabelForRole("admin")).toBe("Mapa");

    const nav = getVisibleMenuSections("relevador").flatMap((s) => s.items);
    expect(nav.find((i) => i.path === "/mapa")?.text).toBe("Mi mapa");

    const home = getVisibleHomeCards("relevador");
    expect(home.find((c) => c.to === "/mapa")?.title).toBe("Mi mapa");

    expect(resolveBreadcrumbLabel("/mapa", "relevador")).toBe("Mi mapa");
    expect(resolveBreadcrumbLabel("/mapa", "admin")).toBe("Mapa");
  });

  it("MapPage inspector sin geolocalización ni catálogos globales", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("isInspectorMapa");
    expect(mapPage).toContain('data-inspector-mapa="true"');
    expect(mapPage).toContain("MapaFiltrosRangoFechas");
    expect(mapPage).toContain('variant="inspector"');
    expect(read("src/Containers/Mapa/Components/MapaModoTabs.tsx")).toContain("Mis trabajos");
    expect(mapPage).toMatch(/data-inspector-mapa="true"[\s\S]*MapaFiltrosRangoFechas/);
    expect(mapPage).toMatch(/if \(isInspectorMapa\) return[\s\S]*fetchInspectores/);
    expect(mapPage).toMatch(/if \(isInspectorMapa\) return[\s\S]*fetchRubrosCatalogoCached/);
    expect(mapPage).toMatch(/if \(isInspectorMapa\) return[\s\S]*fetchDistritosCatalogo/);
  });

  it("admin conserva tabs globales en MapaModoTabs", () => {
    const tabs = read("src/Containers/Mapa/Components/MapaModoTabs.tsx");
    expect(tabs).toContain("Geolocalización");
    expect(tabs).toContain('variant === "inspector"');
  });

  it("resumen operativo inspector usa conteo de features y sin CSV", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toMatch(/data-inspector-mapa="true"[\s\S]*isInspectorView/);

    const panel = read("src/Containers/Mapa/Components/PanelResumenOperativo.tsx");
    expect(panel).toContain("meta?.total_operativos ?? features.length");
    expect(panel).toMatch(/!isInspectorView[\s\S]*Descargar reporte CSV/);
  });
});
