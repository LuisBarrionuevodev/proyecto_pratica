import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("PERF.4 route code splitting", () => {
  const app = read("src/App.tsx");
  const lazyModules = read("src/routing/lazyRouteModules.tsx");
  const layout = read("src/layouts/AppLayout.tsx");

  it("Mis trabajos y Completar trabajo permanecen eager", () => {
    expect(app).toContain('import Actuaciones from "./Containers/Actuaciones"');
    expect(app).toContain('import CompletarTrabajos from "./Containers/CompletarTrabajos"');
    expect(app).not.toMatch(/lazy\(\s*\(\)\s*=>\s*import\("\.\/Containers\/Actuaciones"\)/);
  });

  it("Mapa e Indicadores se cargan con React.lazy", () => {
    expect(lazyModules).toContain('import("../Containers/Mapa")');
    expect(lazyModules).toContain('import("../Containers/Dashboard")');
    expect(lazyModules).toMatch(/lazy\(/);
    expect(app).toContain("LazyMapa");
    expect(app).toContain("LazyDashboard");
  });

  it("AppLayout envuelve Outlet en Suspense con fallback de módulo", () => {
    expect(layout).toContain("Suspense");
    expect(layout).toContain("RouteModuleFallback");
    expect(read("src/routing/RouteModuleFallback.tsx")).toContain("Cargando módulo");
  });

  it("redirect legacy gestionarDomicilios intacto", () => {
    expect(app).toContain('path="/gestionarDomicilios"');
    expect(app).toContain('<Navigate to="/mapa" replace />');
  });
});
