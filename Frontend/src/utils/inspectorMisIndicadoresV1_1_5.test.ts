import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { getVisibleHomeCards, getVisibleMenuSections } from "../auth/accessConfig";
import { resolveBreadcrumbLabel } from "./breadcrumbLabel";
import {
  indicadoresLabelForRole,
  isMenuPathVisibleForRole,
  isPathAllowedForRole,
} from "../auth/roles";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("V1.1-INSPECTOR.5 — Mis indicadores", () => {
  it("relevador accede a /dashboard con rótulo Mis indicadores", () => {
    expect(isPathAllowedForRole("relevador", "/dashboard")).toBe(true);
    expect(isMenuPathVisibleForRole("relevador", "/dashboard")).toBe(true);
    expect(indicadoresLabelForRole("relevador")).toBe("Mis indicadores");
    expect(indicadoresLabelForRole("admin")).toBe("Indicadores");

    const nav = getVisibleMenuSections("relevador").flatMap((s) => s.items);
    const item = nav.find((i) => i.path === "/dashboard");
    expect(item?.text).toBe("Mis indicadores");

    const home = getVisibleHomeCards("relevador");
    const card = home.find((c) => c.to === "/dashboard");
    expect(card?.title).toBe("Mis indicadores");

    expect(resolveBreadcrumbLabel("/dashboard", "relevador")).toBe("Mis indicadores");
    expect(resolveBreadcrumbLabel("/dashboard", "admin")).toBe("Indicadores");
  });

  it("Panel inspector oculta filtros, catálogos y exportar PDF", () => {
    const panel = read("src/Containers/Dashboard/Components/Panel.tsx");
    expect(panel).toContain("isInspectorIndicadores");
    expect(panel).toContain('data-inspector-indicadores={isInspectorIndicadores ? "true" : undefined}');
    expect(panel).toContain("if (isInspectorIndicadores) return");
    expect(panel).toContain("fetchDistritosCatalogo");
    expect(panel).toContain("fetchInspectores");
    expect(panel).toMatch(/!isInspectorIndicadores[\s\S]*Exportar PDF/);
    expect(panel).toMatch(/!isInspectorIndicadores[\s\S]*dash-distrito-label/);
  });
});
