/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { InspeccionAtencionEstablecimientoFields } from "./InspeccionAtencionEstablecimientoFields";

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

function markupWithoutCss(html: string): string {
  return html.replace(/<style[\s\S]*?<\/style>/g, "");
}

describe("InspeccionAtencionEstablecimientoFields", () => {
  it("renderiza carácter y contrato con opción sin indicar", () => {
    const html = render(
      <InspeccionAtencionEstablecimientoFields
        caracter="ENCARGADO"
        contrato={true}
        onCaracterChange={vi.fn()}
        onContratoChange={vi.fn()}
      />
    );
    expect(html).toContain("Atención en el establecimiento");
    expect(html).toContain("Carácter de quien atendió");
    expect(html).toContain("TITULAR");
    expect(html).toContain("ENCARGADO");
    expect(html).toContain("EMPLEADO");
    expect(html).toContain("OTRO");
    expect(html).toContain("contrato de retiro de residuos sólidos urbanos");
    expect(html).toContain("SÍ");
    expect(html).toContain("NO");
  });

  it("hideHeading omite el título interno", () => {
    const html = render(
      <InspeccionAtencionEstablecimientoFields
        hideHeading
        caracter={null}
        contrato={null}
        onCaracterChange={vi.fn()}
        onContratoChange={vi.fn()}
      />
    );
    expect(html).not.toContain("Atención en el establecimiento");
    expect(html).toContain("Carácter de quien atendió");
  });

  it("sin acta (disabled): grupos visibles y realmente deshabilitados", () => {
    const html = render(
      <InspeccionAtencionEstablecimientoFields
        hideHeading
        showCarnet
        caracter="ENCARGADO"
        contrato={false}
        carnet="si"
        onCaracterChange={vi.fn()}
        onContratoChange={vi.fn()}
        onCarnetChange={vi.fn()}
        disabled
      />
    );
    expect(html).toContain("Carácter de quien atendió");
    expect(html).toContain("carnet de manipulador de alimentos");
    expect(html).toContain("contrato de retiro de residuos sólidos urbanos");
    expect(markupWithoutCss(html)).toContain("Mui-disabled");
    expect(html).toContain("ENCARGADO");
    expect(html).toContain("Mui-selected");
  });

  it("con acta (enabled): no aplica disabled a los selectores", () => {
    const html = render(
      <InspeccionAtencionEstablecimientoFields
        hideHeading
        showCarnet
        caracter={null}
        contrato={null}
        carnet=""
        onCaracterChange={vi.fn()}
        onContratoChange={vi.fn()}
        onCarnetChange={vi.fn()}
      />
    );
    expect(html).toContain("Carácter de quien atendió");
    expect(html).toContain("carnet de manipulador de alimentos");
    expect(html).toContain("contrato de retiro de residuos sólidos urbanos");
    expect(markupWithoutCss(html)).not.toContain("Mui-disabled");
  });

  it("muestra carnet entre carácter y contrato cuando showCarnet", () => {
    const html = render(
      <InspeccionAtencionEstablecimientoFields
        hideHeading
        showCarnet
        caracter={null}
        contrato={null}
        onCaracterChange={vi.fn()}
        onContratoChange={vi.fn()}
        onCarnetChange={vi.fn()}
      />
    );
    const iCaracter = html.indexOf("Carácter de quien atendió");
    const iCarnet = html.indexOf("carnet de manipulador de alimentos");
    const iContrato = html.indexOf("contrato de retiro de residuos sólidos urbanos");
    expect(iCaracter).toBeGreaterThan(-1);
    expect(iCarnet).toBeGreaterThan(iCaracter);
    expect(iContrato).toBeGreaterThan(iCarnet);
  });
});
