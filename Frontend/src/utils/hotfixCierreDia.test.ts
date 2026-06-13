import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  isMenuPathVisibleForRole,
  isPathAllowedForRole,
  RELEVADOR_ALLOWED_PATHS,
  RELEVADOR_INICIO_PATHS,
  ROLE_LABELS,
} from "../auth/roles";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("HOTFIX-CIERRE-DIA RELEVADOR roles", () => {
  it("RELEVADOR ve solo rutas permitidas", () => {
    for (const p of RELEVADOR_ALLOWED_PATHS) {
      expect(isPathAllowedForRole("relevador", p)).toBe(true);
    }
    expect(isPathAllowedForRole("relevador", "/rutasTrabajo")).toBe(false);
    expect(isPathAllowedForRole("relevador", "/dashboard")).toBe(false);
    expect(isPathAllowedForRole("relevador", "/gestionDeUsuarios")).toBe(false);
    expect(isPathAllowedForRole("relevador", "/mapa")).toBe(false);
  });

  it("RELEVADOR inicio solo 3 cards", () => {
    expect(RELEVADOR_INICIO_PATHS).toEqual([
      "/cargarActuacion",
      "/cargarRelevamiento",
      "/relevamientos",
    ]);
    expect(isMenuPathVisibleForRole("relevador", "/cargarActuacion")).toBe(true);
    expect(isMenuPathVisibleForRole("relevador", "/completarTrabajos")).toBe(false);
  });

  it("admin ve todo incluido gestión usuarios", () => {
    expect(isMenuPathVisibleForRole("admin", "/gestionDeUsuarios")).toBe(true);
    expect(isPathAllowedForRole("admin", "/rutasTrabajo")).toBe(true);
  });

  it("usuario no ve gestión usuarios", () => {
    expect(isMenuPathVisibleForRole("usuario", "/gestionDeUsuarios")).toBe(false);
    expect(isPathAllowedForRole("usuario", "/rutasTrabajo")).toBe(true);
  });

  it("label Relevador visible", () => {
    expect(ROLE_LABELS.relevador).toBe("Relevador");
  });
});

describe("HOTFIX-CIERRE-DIA frontend wiring", () => {
  it("NavLeft usa accessConfig unificado", () => {
    expect(read("src/Componets/NavLeft.tsx")).toContain("getVisibleMenuSections");
  });

  it("AppLayout usa RoleRouteGuard", () => {
    expect(read("src/layouts/AppLayout.tsx")).toContain("RoleRouteGuard");
  });

  it("completar trabajo vincula notificacion_id", () => {
    const src = readFileSync(
      resolve(
        process.cwd(),
        "../Backend/app/domains/actuaciones/services/completar_trabajo_cierre_service.py"
      ),
      "utf8"
    );
    expect(src).toContain("_vincular_notificacion_reinspeccion_en_acta");
    expect(src).toContain("act.notificacion_id = ini.notificacion_id");
  });
});
