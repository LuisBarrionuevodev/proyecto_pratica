/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { InspeccionAtencionEstablecimientoFields } from "./InspeccionAtencionEstablecimientoFields";

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
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
    expect(html).toContain("Titular");
    expect(html).toContain("Encargado");
    expect(html).toContain("Empleado");
    expect(html).toContain("Otro");
    expect(html).toContain("contrato de retiro de residuos sólidos urbanos");
    expect(html).toContain("Sí");
    expect(html).toContain("No");
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
});
