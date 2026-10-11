import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("V1.1-INICIO-ABOUT.1", () => {
  it("registra ruta /acerca-de y pantalla institucional", () => {
    const app = read("src/App.tsx");
    const acerca = read("src/Containers/AcercaDe/index.tsx");
    expect(app).toContain('path="/acerca-de"');
    expect(acerca).toContain("setBodyAuthenticatedRoute");
    expect(acerca).toContain("VOLVER AL INICIO");
    expect(acerca).toContain("Derechos de autor y licencia");
    expect(acerca).toContain("en proceso de formalización");
  });

  it("Inicio incluye card Acerca y preview mapa en desktop", () => {
    const grid = read("src/Containers/Inicio/Components/InicioOperacionesGrid.tsx");
    const card = read("src/Containers/Inicio/Components/InicioAccesoCard.tsx");
    const inicio = read("src/Containers/Inicio/index.tsx");
    expect(grid).toContain("InicioAboutCard");
    expect(grid).toContain('lg: 4');
    expect(card).toContain("mapa.jpg");
    expect(card).toContain("MAPA_PATH");
    expect(inicio).toContain("Bienvenido/a");
    expect(inicio).toContain("GLASS_COLORS.textPrimary");
    expect(inicio).toMatch(/textAlign:\s*\{\s*md:\s*"center"/);
  });

  it("card Acerca navega a /acerca-de con CTA CONOCER MÁS", () => {
    const about = read("src/Containers/Inicio/Components/InicioAboutCard.tsx");
    expect(about).toContain('to="/acerca-de"');
    expect(about).toContain("CONOCER MÁS");
    expect(about).toContain("trazabilidad administrativa");
  });
});
