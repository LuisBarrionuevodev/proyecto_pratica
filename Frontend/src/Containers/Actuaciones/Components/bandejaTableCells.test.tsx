/** @jsxImportSource react */

import { createTheme, ThemeProvider } from "@mui/material/styles";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  BandejaTipoActuacionChipCell,
  contraproducenciaBandejaSegment,
  tipoActuacionBandejaSegment,
} from "./bandejaTableCells";

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("bandejaTableCells tipo actuación", () => {
  it("tipoActuacionBandejaSegment formatea con prefijo Tipo:", () => {
    expect(tipoActuacionBandejaSegment("REINSPECCION")).toBe("Tipo: REINSPECCION");
    expect(tipoActuacionBandejaSegment("RATIFICACION DE CLAUSURA")).toBe(
      "Tipo: RATIFICACION DE CLAUSURA"
    );
    expect(tipoActuacionBandejaSegment("  ")).toBe("");
    expect(tipoActuacionBandejaSegment(null)).toBe("");
  });

  it("contraproducenciaBandejaSegment formatea con prefijo Contraproducencia:", () => {
    expect(contraproducenciaBandejaSegment("LOCAL CERRADO")).toBe("Contraproducencia: LOCAL CERRADO");
    expect(contraproducenciaBandejaSegment(null)).toBe("");
  });

  it("BandejaTipoActuacionChipCell renderiza chip outlined", () => {
    const html = render(<BandejaTipoActuacionChipCell tipo="VERIFICAR E INFORMAR" />);
    expect(html).toContain("MuiChip-outlined");
    expect(html).toContain("Tipo: VERIFICAR E INFORMAR");
  });

  it("BandejaTipoActuacionChipCell incluye contraproducencia cuando existe", () => {
    const html = render(
      <BandejaTipoActuacionChipCell tipo="REINSPECCION" contraproducencia="LOCAL CERRADO" />
    );
    expect(html).toContain("Tipo: REINSPECCION");
    expect(html).toContain("Contraproducencia: LOCAL CERRADO");
  });

  it("BandejaTipoActuacionChipCell sin valor muestra guión", () => {
    const html = render(<BandejaTipoActuacionChipCell tipo={null} />);
    expect(html).toContain("—");
    expect(html).not.toContain("MuiChip-outlined");
  });
});
