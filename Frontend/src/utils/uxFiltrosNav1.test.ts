import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { INICIO_ACCESOS } from "../Containers/Inicio/inicioAccesosData";
import { menuSections } from "../constants/menuItems";

describe("menuItems UX-FILTROS-NAV-1", () => {
  it("no expone Configuración en el menú lateral", () => {
    const labels = menuSections.map((s) => s.label);
    const paths = menuSections.flatMap((s) => s.items.map((i) => i.path));
    expect(labels).not.toContain("CONFIGURACIÓN");
    expect(paths).not.toContain("/gestionSistema");
  });

  it("agrupa Operativa con notificaciones, comprobaciones y domicilios", () => {
    const operativa = menuSections.find((s) => s.label === "OPERATIVA");
    expect(operativa).toBeDefined();
    const texts = operativa!.items.map((i) => i.text);
    expect(texts).toContain("Notificaciones gestión");
    expect(texts).toContain("Comprobaciones gestión");
    expect(texts).toContain("Gestionar domicilios");
    expect(texts).toContain("Completar trabajo");
  });

  it("lista Relevamientos y denuncias unificado", () => {
    const listas = menuSections.find((s) => s.label === "LISTAS");
    const texts = listas!.items.map((i) => i.text);
    expect(texts).toContain("Relevamientos y denuncias");
    expect(texts).toContain("Actuaciones");
  });
});

describe("inicioAccesosData", () => {
  it("tiene 14 cards sin configuración (incluye Mi perfil)", () => {
    expect(INICIO_ACCESOS).toHaveLength(14);
    expect(INICIO_ACCESOS.some((c) => c.to === "/gestionSistema")).toBe(false);
    expect(INICIO_ACCESOS.some((c) => c.to === "/gestionarDomicilios")).toBe(true);
  });

  it("incluye módulos operativos principales", () => {
    const paths = INICIO_ACCESOS.map((c) => c.to);
    expect(paths).toContain("/cargarActuacion");
    expect(paths).toContain("/completarTrabajos");
    expect(paths).toContain("/gestionNotificacion");
    expect(paths).toContain("/actasComprobacion");
  });
});

describe("ActuacionesContainer carga inicial", () => {
  it("no dispara buscar automático al montar", () => {
    const path = resolve(process.cwd(), "src/Containers/Actuaciones/ActuacionesContainer.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).not.toMatch(/useEffect\(\(\) => \{\s*void buscar\(/);
    expect(src).toContain("Usá los filtros para buscar actuaciones");
  });
});

describe("FiltroFechas UX-FILTROS-NAV-1", () => {
  it("mantiene Filtrar y Limpiar", () => {
    const path = resolve(process.cwd(), "src/Containers/Actuaciones/Components/FiltroFechas.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("Filtrar");
    expect(src).toContain("Limpiar");
  });
});

describe("FiltroUsuarios UX-FILTROS-NAV-1", () => {
  it("define Buscar y Limpiar", () => {
    const path = resolve(
      process.cwd(),
      "src/Containers/GestionDeUsuarios/Components/FiltroUsuarios.tsx"
    );
    const src = readFileSync(path, "utf8");
    expect(src).toContain("Buscar");
    expect(src).toContain("Limpiar");
  });
});
