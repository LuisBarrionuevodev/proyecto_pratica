/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import { ComprobacionExpedienteOperativoDialog } from "./ComprobacionExpedienteOperativoDialog";

vi.mock("../../../components/feedback", () => ({
  useAppFeedback: () => ({
    warning: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

const baseRow = {
  id: 1,
  acta_comprobacion_num: "200",
  fecha_actuacion: "2026-06-28",
} as IActuacionesPendientesItem;

describe("ComprobacionExpedienteOperativoDialog", () => {
  it("usa chrome CRUD glass con footer Guardar expediente", () => {
    const html = render(
      <ComprobacionExpedienteOperativoDialog
        open
        disablePortal
        row={baseRow}
        expNumero=""
        onExpNumeroChange={() => undefined}
        expFecha=""
        onExpFechaChange={() => undefined}
        modalApiError={null}
        saving={false}
        onGuardar={() => undefined}
        onClose={() => undefined}
      />
    );
    expect(html).toContain("Comprobación");
    expect(html).toContain("Expediente");
    expect(html).toContain("Guardar expediente");
    expect(html).not.toContain("Cancelar");
    expect(html).not.toContain("MuiAlert-standardError");
    expect(html).toContain("rgba(255, 255, 255, 0.04)");
  });
});
