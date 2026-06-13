import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

describe("UX-FILTROS-NAV-2 Actuaciones", () => {
  it("no muestra buscador global ni Refrescar en filtros", () => {
    const path = resolve(process.cwd(), "src/Containers/Actuaciones/Components/FiltroFechas.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).not.toContain("ActuacionGlobalSearchAutocomplete");
    expect(src).not.toContain("Refrescar");
    expect(src).not.toContain("onRefrescar");
  });

  it("OT sin fechas en payload", () => {
    const path = resolve(process.cwd(), "src/Containers/Actuaciones/Components/FiltroFechas.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("otLookup ? null : desde");
  });

  it("entra en estado vacío inicial", () => {
    const path = resolve(process.cwd(), "src/Containers/Actuaciones/ActuacionesContainer.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).not.toMatch(/useEffect\(\(\) => \{\s*void buscar\(/);
    expect(src).toContain("Usá los filtros para buscar actuaciones");
  });

  it("Limpiar vuelve a estado inicial vacío", () => {
    const filtro = resolve(process.cwd(), "src/Containers/Actuaciones/Components/FiltroFechas.tsx");
    const container = resolve(process.cwd(), "src/Containers/Actuaciones/ActuacionesContainer.tsx");
    const filtroSrc = readFileSync(filtro, "utf8");
    const containerSrc = readFileSync(container, "utf8");
    expect(filtroSrc).toContain("onLimpiarLista?.()");
    expect(containerSrc).toContain("onLimpiarLista={limpiarLista}");
  });
});

describe("UX-FILTROS-NAV-2 Establecimientos", () => {
  it("distrito y rubro usan AppSelect con nombre visible", () => {
    const path = resolve(process.cwd(), "src/Containers/Establecimientos/EstablecimientosListPage.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain('label="Distrito"');
    expect(src).toContain('label="Rubro"');
    expect(src).toContain("fetchDistritosCatalogo");
    expect(src).toContain("fetchRubrosCatalogoCached");
    expect(src).not.toContain('label="ID distrito"');
    expect(src).not.toContain('label="ID rubro"');
    expect(src).not.toContain("Refrescar");
  });

  it("envía distrito_id y rubro_id al API (conversión desde catálogo)", () => {
    const path = resolve(process.cwd(), "src/Containers/Establecimientos/EstablecimientosListPage.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("distrito_id: parseOptionalInt(applied.distrito_id)");
    expect(src).toContain("rubro_id: parseOptionalInt(applied.rubro_id)");
    expect(src).toContain("label: d.nombre");
    expect(src).toContain("label: r.nombre");
  });
});

describe("UX-FILTROS-NAV-2 Gestión usuarios", () => {
  it("solo Buscar y Limpiar", () => {
    const path = resolve(
      process.cwd(),
      "src/Containers/GestionDeUsuarios/Components/FiltroUsuarios.tsx"
    );
    const src = readFileSync(path, "utf8");
    expect(src).toContain("Buscar");
    expect(src).toContain("Limpiar");
    expect(src).not.toContain("Refrescar");
  });
});

describe("UX-FILTROS-NAV-2 Denuncias", () => {
  it("Limpiar no dispara onFiltrar con mes actual", () => {
    const path = resolve(process.cwd(), "src/Containers/Relevamientos/Components/FiltroDenuncias.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).toContain("onLimpiarLista?.()");
    expect(src).not.toMatch(/handleLimpiar[\s\S]*onFiltrar\(/);
  });
});

describe("UX-FILTROS-NAV-2 Relevamientos", () => {
  it("sin Refrescar en panel de filtros", () => {
    const path = resolve(process.cwd(), "src/Containers/Relevamientos/Components/FiltroRelevamientos.tsx");
    const src = readFileSync(path, "utf8");
    expect(src).not.toContain("Refrescar");
  });
});
