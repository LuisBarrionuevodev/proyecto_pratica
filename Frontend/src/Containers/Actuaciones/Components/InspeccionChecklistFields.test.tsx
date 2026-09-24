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
  { id: 1, codigo: "TIENE_BANO", nombre: "Baño", orden: 1, tipo_respuesta: "ESTADO" },
  {
    id: 4,
    codigo: "TIENE_COCINA_MESA_TRABAJO",
    nombre: "Cocina / mesa de trabajo",
    orden: 4,
    tipo_respuesta: "ESTADO",
  },
  { id: 5, codigo: "VAJILLA_MANTEL", nombre: "Vajilla / mantel", orden: 5, tipo_respuesta: "ESTADO" },
  {
    id: 6,
    codigo: "TIENE_HABILITACION",
    nombre: "Tiene habilitación",
    orden: 6,
    tipo_respuesta: "SI_NO",
  },
];

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("InspeccionChecklistFields", () => {
  it("renderiza título y opciones BIEN / OBSERVADO para ESTADO", () => {
    const html = render(
      <InspeccionChecklistFields
        catalog={catalog.filter((c) => c.tipo_respuesta === "ESTADO")}
        estados={{}}
        onEstadosChange={vi.fn()}
      />
    );
    expect(html).toContain("Condiciones verificadas");
    expect(html).toContain("BIEN");
    expect(html).toContain("OBSERVADO");
    expect(html).toContain("—");
  });

  it("renderiza SÍ / NO para SI_NO", () => {
    const html = render(
      <InspeccionChecklistFields
        catalog={[catalog[3]]}
        estados={{}}
        onEstadosChange={vi.fn()}
      />
    );
    expect(html).toContain("Tiene habilitación");
    expect(html).toContain("SÍ");
    expect(html).toContain("NO");
    expect(html).not.toContain("OBSERVADO");
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
        orden: 4,
        tipo_respuesta: "ESTADO",
      })
    ).toBe("Cocina / cuadra");
    expect(
      displayItemNombre({
        id: 1,
        codigo: "TIENE_BANO",
        nombre: "Baño",
        orden: 1,
        tipo_respuesta: "ESTADO",
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

  it("readOnly muestra SI seleccionado en habilitación", () => {
    const html = render(
      <InspeccionChecklistFields
        catalog={[catalog[3]]}
        estados={{ 6: "SI" }}
        onEstadosChange={vi.fn()}
        readOnly
      />
    );
    expect(html).toContain("Mui-disabled");
    expect(html).toContain('value="SI"');
    expect(html).toContain("Mui-selected");
  });
});
