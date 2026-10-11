import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("V1.1-INICIO-ABOUT.1A", () => {
  it("registra ruta /acerca-de y pantalla institucional", () => {
    const app = read("src/App.tsx");
    const acerca = read("src/Containers/AcercaDe/index.tsx");
    expect(app).toContain('path="/acerca-de"');
    expect(acerca).toContain("VOLVER AL INICIO");
  });

  it("desktop: tres filas (operativas, mapa hero, acerca)", () => {
    const grid = read("src/Containers/Inicio/Components/InicioOperacionesGrid.tsx");
    const mapHero = read("src/Containers/Inicio/Components/InicioMapaHeroCard.tsx");
    const card = read("src/Containers/Inicio/Components/InicioAccesoCard.tsx");
    expect(grid).toContain("InicioMapaHeroCard");
    expect(grid).toContain("operationalCards");
    expect(grid).toContain('display: { xs: "none", md: "flex" }');
    expect(mapHero).toContain("mapa.jpg");
    expect(mapHero).toContain("primitiveWhite");
    expect(card).not.toContain("mapa.jpg");
  });

  it("mobile/tablet mantiene grilla clásica con mapa en card estándar", () => {
    const grid = read("src/Containers/Inicio/Components/InicioOperacionesGrid.tsx");
    expect(grid).toContain('display: { xs: "block", md: "none" }');
    expect(grid).toContain('lg: 3');
  });

  it("encabezado centrado en desktop e ícono de calendario", () => {
    const inicio = read("src/Containers/Inicio/index.tsx");
    expect(inicio).toContain("CalendarMonthOutlinedIcon");
    expect(inicio).toContain("Bienvenido/a");
    expect(inicio).toMatch(/textAlign:\s*\{\s*md:\s*"center"/);
  });
});
