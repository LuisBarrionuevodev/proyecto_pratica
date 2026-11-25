/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { AppButton } from "./AppButton";

const theme = createTheme();

function renderButton(ui: ReactElement): string {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("AppButton", () => {
  it("envuelve el rótulo en un span estable que Chrome Translate no debe reescribir", () => {
    const html = renderButton(<AppButton>Guardar fotos</AppButton>);
    expect(html).toContain("Guardar fotos");
    expect(html).toContain("notranslate");
    expect(html).toContain('translate="no"');
    expect(html).toMatch(/<span[^>]*>Guardar fotos<\/span>/);
  });

  it("sigue mostrando el rótulo con loading (spinner aparte del texto)", () => {
    const html = renderButton(
      <AppButton loading dsVariant="primary">
        GUARDAR FOTOS
      </AppButton>
    );
    expect(html).toContain("GUARDAR FOTOS");
    expect(html).toMatch(/<span[^>]*>GUARDAR FOTOS<\/span>/);
    expect(html).toContain("MuiCircularProgress");
  });
});
