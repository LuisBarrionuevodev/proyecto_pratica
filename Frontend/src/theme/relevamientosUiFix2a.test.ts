import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("HOTFIX V1.1-UI-FIX.2A — catálogos Relevamientos dark", () => {
  it("CSS dark scoped con --d-text-primary y portal", () => {
    const css = read("src/Containers/CargarRelevamientos/styles/relevamientosGlideCatalogDark.css");
    expect(css).toContain('[data-theme="dark"]');
    expect(css).toContain("data-relevamiento-glide-carga");
    expect(css).toContain("--d-text-primary");
    expect(css).toContain("#portal");
    expect(css).not.toContain('[data-theme="light"]');
    expect(css).not.toContain("text-inverse");
  });

  it("grilla Relevamientos importa estilos y marca el contenedor", () => {
    const grid = read("src/Containers/CargarRelevamientos/Components/TablaCargarRelevamientosGlideStyled.tsx");
    expect(grid).toContain("relevamientosGlideCatalogDark.css");
    expect(grid).toContain("data-relevamiento-glide-carga");
  });
});
