/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { NumeroEsquinaFreeEditor } from "./NumeroEsquinaFreeEditor";

vi.mock("../../../api/geolocalizacionApi", () => ({
  fetchCallesCatalogo: vi.fn(),
}));

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("NumeroEsquinaFreeEditor", () => {
  it("renderiza toggle número/esquina sin Autocomplete de catálogo", () => {
    const html = render(
      <NumeroEsquinaFreeEditor
        value="450"
        onChange={() => undefined}
        label="Número o referencia"
      />
    );
    expect(html).toContain("Número");
    expect(html).toContain("Esquina");
    expect(html).not.toContain("MuiAutocomplete");
  });

  it("modo esquina usa input libre sin Autocomplete", () => {
    const html = render(
      <NumeroEsquinaFreeEditor
        value="Av. Corrientes"
        initialMode="ESQUINA"
        onChange={() => undefined}
        label="Número o referencia"
      />
    );
    expect(html).toContain("esquina");
    expect(html).not.toContain("MuiAutocomplete");
  });

  it("modo compacto no renderiza label Número o referencia", () => {
    const html = render(
      <NumeroEsquinaFreeEditor value="450" onChange={() => undefined} compact />
    );
    expect(html).toContain('data-testid="numero-esquina-compact"');
    expect(html).not.toContain("Número o referencia");
  });

  it("modo compacto mantiene toggle e input en el mismo contenedor", () => {
    const html = render(
      <NumeroEsquinaFreeEditor value="450" onChange={() => undefined} compact />
    );
    expect(html).toContain('data-testid="numero-esquina-compact"');
    expect(html).toContain('data-testid="numero-esquina-compact-row"');
    expect(html).toContain('data-testid="numero-esquina-compact-label-spacer"');
    expect(html).toContain("Esquina");
    expect(html).toContain("MuiOutlinedInput");
    expect(html.indexOf("MuiToggleButtonGroup-root")).toBeLessThan(html.indexOf("MuiOutlinedInput-root"));
  });
});
