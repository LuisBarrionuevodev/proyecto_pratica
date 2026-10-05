import { describe, expect, it } from "vitest";

import { getVisibleHomeCards, getVisibleMenuSections } from "./accessConfig";
import {
  isMenuPathVisibleForRole,
  isPathAllowedForRole,
  postLoginPathForRole,
  RELEVAMIENTO_ALLOWED_PATHS,
  RELEVAMIENTO_INICIO_PATHS,
} from "./roles";

describe("V1.1-RELEVAMIENTO-ROLE.1 — menú y rutas", () => {
  it("solo Inicio, carga, gestión y perfil", () => {
    for (const p of RELEVAMIENTO_ALLOWED_PATHS) {
      expect(isPathAllowedForRole("relevamiento", p)).toBe(true);
      expect(isMenuPathVisibleForRole("relevamiento", p)).toBe(true);
    }
    expect(isPathAllowedForRole("relevamiento", "/actuaciones")).toBe(false);
    expect(isPathAllowedForRole("relevamiento", "/rutasTrabajo")).toBe(false);
    expect(isPathAllowedForRole("relevamiento", "/dashboard")).toBe(false);
    expect(isPathAllowedForRole("relevamiento", "/mapa")).toBe(false);
    expect(isPathAllowedForRole("relevamiento", "/gestionDeUsuarios")).toBe(false);
    expect(isPathAllowedForRole("relevamiento", "/cargarActuacion")).toBe(false);
  });

  it("cards de inicio acotadas", () => {
    const cards = getVisibleHomeCards("relevamiento").map((c) => c.to);
    expect(cards).toHaveLength(RELEVAMIENTO_INICIO_PATHS.length);
    for (const p of RELEVAMIENTO_INICIO_PATHS) {
      expect(cards).toContain(p);
    }
  });

  it("menú lateral mínimo", () => {
    const paths = getVisibleMenuSections("relevamiento").flatMap((s) => s.items.map((i) => i.path));
    expect(paths).toContain("/inicio");
    expect(paths).toContain("/cargarRelevamiento");
    expect(paths).toContain("/relevamientos");
    expect(paths).toContain("/perfil");
    expect(paths).not.toContain("/actuaciones");
    expect(paths).not.toContain("/completarTrabajos");
  });

  it("login redirige a carga de relevamientos", () => {
    expect(postLoginPathForRole("relevamiento")).toBe("/cargarRelevamiento");
    expect(postLoginPathForRole("usuario")).toBe("/inicio");
  });
});
