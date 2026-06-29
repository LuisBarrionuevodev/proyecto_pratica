/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import { NotificacionDetalleDocumentalDialog } from "../components/NotificacionDetalleDocumentalDialog";

vi.mock("../../../components/feedback", () => ({
  useAppFeedback: () => ({
    warning: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

vi.mock("../../../api/actuacionesPendientesApi", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../../api/actuacionesPendientesApi")>();
  return {
    ...mod,
    fetchNotificacionProrrogaExpedientes: vi.fn().mockResolvedValue({ items: [], resumen: {} }),
  };
});

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

const baseRow = {
  id: 1,
  acta_notificacion_num: "100",
  fecha_actuacion: "2026-06-28",
  dias_restantes: 3,
  source_type: "NOTIFICACION",
  calle: "San Martín",
  numero: "100",
} as IActuacionesPendientesItem;

describe("NotificacionDetalleDocumentalDialog", () => {
  it("usa chrome CRUD glass sin Cancelar", () => {
    const html = render(
      <NotificacionDetalleDocumentalDialog
        open
        disablePortal
        row={baseRow}
        variant="documental"
        esReinspeccionNotificacion
        expNumero=""
        onExpNumeroChange={() => undefined}
        expFecha=""
        onExpFechaChange={() => undefined}
        prorrogaDias="0"
        onProrrogaDiasChange={() => undefined}
        fieldErrors={{}}
        modalApiError={null}
        saving={false}
        onGuardar={async () => ({ ok: true, volvioEnPlazo: false })}
        onClose={() => undefined}
      />
    );
    expect(html).toContain("Notificación");
    expect(html).toContain("Notificación detalle");
    expect(html).not.toContain("Reinspección por notificación");
    expect(html).not.toContain(">Prórroga<");
    expect(html).not.toContain("Cancelar");
    expect(html).not.toContain("MuiAlert-standardError");
    expect(html).toContain("rgba(255, 255, 255, 0.04)");
  });

  it("modo prórroga usa campos glass en grilla de alta", () => {
    const html = render(
      <NotificacionDetalleDocumentalDialog
        open
        disablePortal
        row={baseRow}
        variant="soloExpediente"
        expNumero=""
        onExpNumeroChange={() => undefined}
        expFecha=""
        onExpFechaChange={() => undefined}
        prorrogaDias="0"
        onProrrogaDiasChange={() => undefined}
        fieldErrors={{}}
        modalApiError={null}
        saving={false}
        onGuardar={async () => ({ ok: true, volvioEnPlazo: false })}
        onClose={() => undefined}
      />
    );
    expect(html).toContain("Notificación detalle");
    expect(html).not.toContain(">Prórroga<");
    expect(html).toContain("Alta de expediente de prórroga");
    expect(html).toContain("Guardar expediente");
    expect(html).toContain("rgba(255, 255, 255, 0.04)");
  });
});
