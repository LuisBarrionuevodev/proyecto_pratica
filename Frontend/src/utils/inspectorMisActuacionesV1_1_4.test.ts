import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { getVisibleHomeCards, getVisibleMenuSections } from "../auth/accessConfig";
import {
  actuacionesLabelForRole,
  isMenuPathVisibleForRole,
  isPathAllowedForRole,
} from "../auth/roles";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("V1.1-INSPECTOR.4 — Mis actuaciones", () => {
  it("relevador accede a /actuaciones con rótulo Mis actuaciones", () => {
    expect(isPathAllowedForRole("relevador", "/actuaciones")).toBe(true);
    expect(isMenuPathVisibleForRole("relevador", "/actuaciones")).toBe(true);
    expect(actuacionesLabelForRole("relevador")).toBe("Mis actuaciones");
    expect(actuacionesLabelForRole("admin")).toBe("Actuaciones");

    const nav = getVisibleMenuSections("relevador").flatMap((s) => s.items);
    const item = nav.find((i) => i.path === "/actuaciones");
    expect(item?.text).toBe("Mis actuaciones");

    const home = getVisibleHomeCards("relevador");
    const card = home.find((c) => c.to === "/actuaciones");
    expect(card?.title).toBe("Mis actuaciones");
  });

  it("relevador no ve cargar actuaciones ni exportar en bandeja", () => {
    expect(isPathAllowedForRole("relevador", "/cargarActuacion")).toBe(false);
    const container = read("src/Containers/Actuaciones/ActuacionesContainer.tsx");
    expect(container).toContain("isInspectorReadOnly");
    expect(container).toContain("hideRowActions={isInspectorReadOnly}");
    expect(container).toContain("enableEditing={!isInspectorReadOnly}");
    expect(container).toContain("exportToolbar={isInspectorReadOnly ? null : actuacionesExportToolbar}");
    expect(container).toContain("hideInspectorFilter={isInspectorReadOnly}");
  });
});
