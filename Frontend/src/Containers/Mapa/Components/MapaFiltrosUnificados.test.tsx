import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("MapaFiltrosUnificados — Realizados", () => {
  const filtro = read("src/Containers/Mapa/Components/MapaFiltrosUnificados.tsx");

  it("usa estilos compartidos con Mapa Pendientes (filtroItemStyles + appearance dense)", () => {
    expect(filtro).toContain("filtroItemStyles");
    expect(filtro).toContain("filtroContainerStyles");
    expect(filtro).toContain('appearance="dense"');
    expect(filtro).not.toContain("mapaOperativoFieldSx");
    expect(filtro).not.toContain('appearance="glass"');
  });

  it("no muestra Definición ni tipos legacy", () => {
    expect(filtro).not.toContain("Definición");
    expect(filtro).not.toContain("MAPA_DEFINICION_OPTIONS");
    expect(filtro).not.toContain("Denuncia");
    expect(filtro).not.toContain("Transporte");
    expect(filtro).not.toContain("Oficio");
    expect(filtro).not.toContain("Notificación");
    expect(filtro).not.toContain("Relevamiento");
  });

  it("muestra Rubro con default Todos", () => {
    expect(filtro).toContain('label="Rubro"');
    expect(filtro).toContain('data-testid="mapa-realizados-filtro-rubro"');
    expect(filtro).toContain("rubroOptions");
  });

  it("conserva filtro Tipo operativo", () => {
    expect(filtro).toContain('label="Tipo"');
    expect(filtro).toContain('data-testid="mapa-realizados-filtro-tipo"');
    expect(filtro).toContain("MAPA_TIPO_INICIADOR_OPTIONS");
  });
});

describe("useMapaOperativo — rubro Realizados", () => {
  it("envía rubro_id al API cuando hay valor", () => {
    const hook = read("src/Containers/Mapa/hooks/useMapaOperativo.ts");
    expect(hook).toContain("mapaRealizadosRubroQueryValue(p.rubroId");
    expect(hook).toContain("rubro_id:");
    expect(hook).not.toContain("definicion");
  });
});

describe("MapPage — catálogo rubros", () => {
  it("carga rubros y conecta filtro", () => {
    const mapPage = read("src/Containers/Mapa/MapPage.tsx");
    expect(mapPage).toContain("fetchRubrosCatalogoCached");
    expect(mapPage).toContain("realizadoRubroId");
    expect(mapPage).not.toContain("realizadoDefinicion");
  });
});
