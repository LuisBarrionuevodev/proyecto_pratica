/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import {
  displayItemNombre,
  InspeccionChecklistFields,
} from "./InspeccionChecklistFields";
import type { IItemActaInspeccionCatalogItem } from "../../../api/itemActaInspeccionCatalogApi";

const theme = createTheme();

const catalog: IItemActaInspeccionCatalogItem[] = [
  { id: 1, codigo: "TIENE_BANO", nombre: "Baño", activo: true, orden: 1 },
  { id: 4, codigo: "TIENE_COCINA_MESA_TRABAJO", nombre: "Cocina / mesa de trabajo", activo: true, orden: 4 },
  { id: 5, codigo: "VAJILLA_MANTEL", nombre: "Vajilla / mantel", activo: true, orden: 5 },
];

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("InspeccionChecklistFields", () => {
  it("renderiza título y opciones BIEN / OBSERVADO", () => {
    const html = render(
      <InspeccionChecklistFields
        catalog={catalog}
        estados={{}}
        onEstadosChange={vi.fn()}
      />
    );
    expect(html).toContain("Condiciones verificadas");
    expect(html).toContain("BIEN");
    expect(html).toContain("OBSERVADO");
    expect(html).toContain("—");
  });

  it("muestra Cocina / cuadra y no Cocina / mesa de trabajo", () => {
    const html = render(
      <InspeccionChecklistFields
        catalog={catalog}
        estados={{}}
        onEstadosChange={vi.fn()}
      />
    );
    expect(html).toContain("Cocina / cuadra");
    expect(html).not.toContain("Cocina / mesa de trabajo");
  });

  it("displayItemNombre renombra solo el código de cocina", () => {
    expect(
      displayItemNombre({
        id: 4,
        codigo: "TIENE_COCINA_MESA_TRABAJO",
        nombre: "Cocina / mesa de trabajo",
        activo: true,
        orden: 4,
      })
    ).toBe("Cocina / cuadra");
    expect(
      displayItemNombre({
        id: 1,
        codigo: "TIENE_BANO",
        nombre: "Baño",
        activo: true,
        orden: 1,
      })
    ).toBe("Baño");
  });

  it("deshabilita controles cuando disabled=true", () => {
    const html = render(
      <InspeccionChecklistFields
        catalog={catalog}
        estados={{}}
        onEstadosChange={vi.fn()}
        disabled
      />
    );
    expect(html).toContain("Mui-disabled");
  });

  it("marca selección exclusiva en estado BIEN", () => {
    const html = render(
      <InspeccionChecklistFields
        catalog={[catalog[0]]}
        estados={{ 1: "BIEN" }}
        onEstadosChange={vi.fn()}
      />
    );
    expect(html).toContain('value="BIEN"');
    expect(html).toContain("Mui-selected");
  });

  it("readOnly deshabilita controles pero mantiene selección visible", () => {
    const html = render(
      <InspeccionChecklistFields
        catalog={[catalog[0]]}
        estados={{ 1: "OBSERVADO" }}
        onEstadosChange={vi.fn()}
        readOnly
      />
    );
    expect(html).toContain("Mui-disabled");
    expect(html).toContain('value="OBSERVADO"');
    expect(html).toContain("Mui-selected");
  });
});
