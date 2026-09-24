/** @jsxImportSource react */
import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { INICIO_ACCESOS } from "../Inicio/inicioAccesosData";
import { menuSections } from "../../constants/menuItems";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("PR6C.12 redirect /gestionarDomicilios → /mapa", () => {
  it("App.tsx redirige la ruta legacy", () => {
    const app = read("src/App.tsx");
    expect(app).toContain('path="/gestionarDomicilios"');
    expect(app).toContain('<Navigate to="/mapa" replace />');
    expect(app).not.toContain('element={<GestionarDomicilios');
  });

  it("index GestionarDomicilios también redirige", () => {
    const index = read("src/Containers/GestionarDomicilios/index.tsx");
    expect(index).toContain('<Navigate to="/mapa" replace />');
    expect(index).not.toContain("import GestionarDomiciliosContainer");
    expect(index).not.toContain("<GestionarDomiciliosContainer");
  });

  it("wrapper temporal eliminado (PR6C.15); redirect sin container", () => {
    const index = read("src/Containers/GestionarDomicilios/index.tsx");
    expect(index).toContain('<Navigate to="/mapa" replace />');
    expect(index).not.toContain("import GestionarDomiciliosContainer");
    expect(index).not.toContain("<GestionarDomiciliosContainer");
    const app = read("src/App.tsx");
    expect(app).not.toContain("GestionarDomiciliosContainer");
    expect(existsSync(resolve(process.cwd(), "src/Containers/GestionarDomicilios/GestionarDomiciliosContainer.tsx"))).toBe(
      false
    );
  });
});

describe("PR6C.12 menú y navegación sin duplicados", () => {
  it("menú lateral no muestra Gestionar domicilios", () => {
    const paths = menuSections.flatMap((s) => s.items.map((i) => i.path));
    const texts = menuSections.flatMap((s) => s.items.map((i) => i.text));
    expect(paths).not.toContain("/gestionarDomicilios");
    expect(texts).not.toContain("Gestionar domicilios");
    expect(paths).toContain("/mapa");
    const mapaEntries = paths.filter((p) => p === "/mapa");
    expect(mapaEntries).toHaveLength(1);
  });

  it("Inicio no duplica acceso a domicilios", () => {
    const paths = INICIO_ACCESOS.map((c) => c.to);
    expect(paths).not.toContain("/gestionarDomicilios");
    expect(paths).toContain("/mapa");
    expect(INICIO_ACCESOS).toHaveLength(13);
  });

  it("Actuaciones enlaza a /mapa", () => {
    const actuaciones = read("src/Containers/Actuaciones/ActuacionesContainer.tsx");
    expect(actuaciones).toContain('navigate("/mapa")');
    expect(actuaciones).not.toContain("/gestionarDomicilios");
    expect(actuaciones).toContain("Ir a Mapa");
  });
});

describe("PR6C.12 Mapa y permisos", () => {
  it("/mapa mantiene Geolocalización y deep link realizados", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("MapaDomiciliosGeolocalizacionView");
    expect(mapPage).toContain('"realizados"');
    expect(mapPage).toContain("useSearchParams");
  });

  it("roles no bloquean /mapa para usuario", () => {
    const roles = read("src/auth/roles.ts");
    expect(roles).toContain('p !== "/gestionDeUsuarios"');
    expect(roles).not.toContain("/gestionarDomicilios");
  });
});
