/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { ComprobacionOficioOperativoDialog } from "./ComprobacionOficioOperativoDialog";

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

describe("ComprobacionOficioOperativoDialog", () => {
  it("usa chrome CRUD glass sin Cancelar", () => {
    const html = render(
      <ComprobacionOficioOperativoDialog
        open
        disablePortal
        row={{
          id: 1,
          acta_comprobacion_num: "300",
          fecha_actuacion: "2026-06-28",
        }}
        juzgados={[]}
        documental={null}
        documentalLoading={false}
        documentalError={null}
        oficios={[]}
        oficiosLoading={false}
        oficiosError={null}
        onDocumentalUpdated={async () => undefined}
        defaultFechaAlta="2026-06-28"
        modalApiError={null}
        saving={false}
        onGuardarAlta={async () => undefined}
        onClose={() => undefined}
      />
    );
    expect(html).toContain("Comprobación");
    expect(html).toContain("Oficio");
    expect(html).not.toContain("Cancelar");
    expect(html).not.toContain("MuiAlert-standardError");
    expect(html).toContain("rgba(255, 255, 255, 0.04)");
  });
});
