/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { ReinspeccionOperativaAccionCell } from "./ReinspeccionOperativaAccionCell";
import {
  prorrogaSuccessMessage,
  volvioEnPlazoDesdeExpedienteMeta,
} from "../utils/prorrogaSuccessMessage";

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

describe("ReinspeccionOperativaAccionCell", () => {
  it("muestra solo botón Dar prórroga sin Ver detalle", () => {
    const html = render(<ReinspeccionOperativaAccionCell onProrroga={() => undefined} />);
    expect(html).toContain(">Dar prórroga<");
    expect(html).not.toContain(">Prórroga<");
    expect(html).not.toContain("Ver detalle");
    expect(html).not.toContain("Detalle");
  });

  it("expone handler onProrroga", () => {
    const onProrroga = vi.fn();
    expect(typeof onProrroga).toBe("function");
  });
});

describe("prorrogaSuccessMessage", () => {
  it("mensaje base cuando no volvió a en plazo", () => {
    expect(prorrogaSuccessMessage(false)).toBe("Expediente registrado correctamente.");
  });

  it("mensaje extendido cuando volvió a en plazo", () => {
    expect(prorrogaSuccessMessage(true)).toBe(
      "Expediente registrado correctamente. La notificación volvió a estar en plazo."
    );
  });

  it("detecta EN_PLAZO desde meta API", () => {
    expect(volvioEnPlazoDesdeExpedienteMeta("EN_PLAZO")).toBe(true);
    expect(volvioEnPlazoDesdeExpedienteMeta("PENDIENTE_REINSPECCION")).toBe(false);
  });
});
