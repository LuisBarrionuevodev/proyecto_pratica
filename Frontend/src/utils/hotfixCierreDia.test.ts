import { describe, expect, it } from "vitest";
import {
  completarTrabajosLabelForRole,
  isMenuPathVisibleForRole,
  isPathAllowedForRole,
  RELEVADOR_ALLOWED_PATHS,
  ROLE_LABELS,
} from "../auth/roles";

describe("INSPECTOR.3 — rol relevador / Completar mis trabajos", () => {
  it("relevador solo inicio, completar y perfil", () => {
    for (const p of RELEVADOR_ALLOWED_PATHS) {
      expect(isPathAllowedForRole("relevador", p)).toBe(true);
    }
    expect(isPathAllowedForRole("relevador", "/rutasTrabajo")).toBe(false);
    expect(isPathAllowedForRole("relevador", "/dashboard")).toBe(false);
    expect(isPathAllowedForRole("relevador", "/gestionDeUsuarios")).toBe(false);
    expect(isPathAllowedForRole("relevador", "/mapa")).toBe(false);
    expect(isPathAllowedForRole("relevador", "/cargarActuacion")).toBe(false);
    expect(isPathAllowedForRole("relevador", "/relevamientos")).toBe(false);
  });

  it("menú relevador muestra Completar mis trabajos", () => {
    expect(isMenuPathVisibleForRole("relevador", "/completarTrabajos")).toBe(true);
    expect(isMenuPathVisibleForRole("relevador", "/cargarActuacion")).toBe(false);
    expect(completarTrabajosLabelForRole("relevador")).toBe("Completar mis trabajos");
    expect(completarTrabajosLabelForRole("admin")).toBe("Completar trabajo");
  });

  it("admin conserva acceso global", () => {
    expect(isMenuPathVisibleForRole("admin", "/gestionDeUsuarios")).toBe(true);
    expect(isPathAllowedForRole("admin", "/rutasTrabajo")).toBe(true);
  });

  it("usuario sin gestión usuarios", () => {
    expect(isMenuPathVisibleForRole("usuario", "/gestionDeUsuarios")).toBe(false);
    expect(isPathAllowedForRole("usuario", "/rutasTrabajo")).toBe(true);
  });

  it("label visible Inspector", () => {
    expect(ROLE_LABELS.relevador).toBe("Inspector");
  });
});
