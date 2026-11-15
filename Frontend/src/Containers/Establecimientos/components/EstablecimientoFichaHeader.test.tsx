/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { IEstablecimientoOperativoDetail } from "../../../api/establecimientosOperativosApi";
import { EstablecimientoFichaHeader } from "./EstablecimientoFichaHeader";

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

function detalle(partial: Partial<IEstablecimientoOperativoDetail>): IEstablecimientoOperativoDetail {
  return {
    id: 12,
    domicilio_id: 3,
    created_at: null,
    updated_at: null,
    calle: "San Martín",
    numero: "100",
    calle_normalizada: "San Martín",
    contrib_apellido: "Pérez",
    contrib_nombre: "Ana",
    razon_social: null,
    documento: "20123456789",
    rubro_nombre: "Panadería",
    distrito_id: 1,
    distrito_nombre: "Distrito 1",
    domicilio_texto: "San Martín 100",
    actuaciones_count: 2,
    ultima_actuacion_fecha: null,
    nombre_local: "Kiosco 24",
    ...partial,
  };
}

describe("EstablecimientoFichaHeader UX.1", () => {
  it("muestra persona física, local y domicilio con acciones discretas", () => {
    const html = render(
      <EstablecimientoFichaHeader
        detalle={detalle({})}
        canCorrect
        onCorregir={() => undefined}
      />
    );
    expect(html).toContain("Ana Pérez");
    expect(html).toContain("DNI/CUIT: 20123456789");
    expect(html).toContain("Kiosco 24");
    expect(html).toContain("Rubro: Panadería");
    expect(html).toContain("San Martín 100");
    expect(html).toContain("Distrito: Distrito 1");
    expect(html).toContain("Corregir contribuyente");
    expect(html).not.toContain("Vincular a contribuyente existente");
    expect(html).toContain("Corregir datos del local");
    expect(html).toContain("Corregir domicilio");
    expect(html).toContain("Contribuyente");
    expect(html).toContain("Establecimiento");
    expect(html).toContain("Domicilio");
  });

  it("prioriza razón social y usa placeholder si el local no tiene nombre", () => {
    const html = render(
      <EstablecimientoFichaHeader
        detalle={detalle({
          razon_social: "Panadería El Sol S.A.",
          nombre_local: "  ",
          rubro_nombre: null,
          distrito_nombre: null,
        })}
        canCorrect
        onCorregir={() => undefined}
      />
    );
    expect(html).toContain("Panadería El Sol S.A.");
    expect(html).toContain("Sin nombre registrado");
    expect(html).toContain("Rubro: —");
    expect(html).not.toContain("Distrito:");
    expect(html).not.toContain("Ana Pérez");
  });

  it("oculta acciones si el rol no puede corregir", () => {
    const html = render(
      <EstablecimientoFichaHeader detalle={detalle({})} canCorrect={false} onCorregir={() => undefined} />
    );
    expect(html).toContain("Ana Pérez");
    expect(html).not.toContain("Corregir contribuyente");
    expect(html).not.toContain("Vincular a contribuyente existente");
    expect(html).not.toContain("Corregir datos del local");
    expect(html).not.toContain("Corregir domicilio");
  });

  it("envuelve nombres y direcciones largas sin inventar titular", () => {
    const html = render(
      <EstablecimientoFichaHeader
        detalle={detalle({
          contrib_nombre: null,
          contrib_apellido: null,
          razon_social: null,
          documento: null,
          nombre_local: "Local con un nombre extraordinariamente largo para comprobar el corte",
          domicilio_texto:
            "Avenida de los Inmigrantes de la República Argentina 1234 esquina Boulevard del Libertador",
        })}
        canCorrect={false}
        onCorregir={() => undefined}
      />
    );
    expect(html).toContain("—");
    expect(html).toContain("DNI/CUIT: —");
    expect(html).toContain("break-word");
    expect(html).not.toContain("Establecimiento #12");
  });
});
