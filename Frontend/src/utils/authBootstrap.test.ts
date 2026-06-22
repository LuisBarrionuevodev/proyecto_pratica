import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { getVisibleHomeCards } from "../auth/accessConfig";
import { RELEVADOR_INICIO_PATHS } from "../auth/roles";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("HOTFIX auth bootstrap — carga inicial sin F5", () => {
  it("AppSessionProvider no fetch perfil sin token", () => {
    const src = read("src/auth/AppSessionProvider.tsx");
    expect(src).toContain('localStorage.getItem("access_token")');
    expect(src).toContain('setStatus("unauthenticated")');
    expect(src).toMatch(/if\s*\(\s*!token\s*\)/);
  });

  it("login dispara refresh de sesión tras guardar token", () => {
    const src = read("src/Containers/Login/Components/LoginBox.tsx");
    expect(src).toContain("notifyAuthSessionRefresh");
    expect(src).toMatch(/setItem\([\s\S]*notifyAuthSessionRefresh/);
  });

  it("logout y 401 notifican refresh de sesión", () => {
    expect(read("src/Componets/TopBar.tsx")).toContain("notifyAuthSessionRefresh");
    expect(read("src/api/apiClient.ts")).toContain("notifyAuthSessionRefresh");
  });

  it("InicioOperacionesGrid espera status ready antes de armar cards", () => {
    const src = read("src/Containers/Inicio/Components/InicioOperacionesGrid.tsx");
    expect(src).toContain('status !== "ready"');
    expect(src).toContain('status === "loading"');
    expect(src).not.toMatch(/if\s*\(\s*!role\s*\)\s*return\s*\[\]/);
  });

  it("RoleRouteGuard muestra loading mientras bootstrap", () => {
    const src = read("src/layouts/RoleRouteGuard.tsx");
    expect(src).toContain('status === "loading"');
    expect(src).toContain("CircularProgress");
    expect(src).not.toMatch(/if\s*\(\s*status\s*===\s*"loading"\s*\)\s*\{\s*return\s*null/);
  });

  it("Relevador: 4 cards tras sesión ready", () => {
    const cards = getVisibleHomeCards("relevador").map((c) => c.to);
    expect(cards).toHaveLength(RELEVADOR_INICIO_PATHS.length);
    for (const p of RELEVADOR_INICIO_PATHS) {
      expect(cards).toContain(p);
    }
  });

  it("Admin: cards de inicio no vacías", () => {
    const cards = getVisibleHomeCards("admin");
    expect(cards.length).toBeGreaterThan(4);
  });
});
