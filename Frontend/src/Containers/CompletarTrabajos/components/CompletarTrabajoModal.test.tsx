/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { CompletarTrabajoModal } from "./CompletarTrabajoModal";

vi.mock("../../../components/feedback", () => ({
  useAppFeedback: () => ({
    warning: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

vi.mock("../../../api/completarTrabajoApi", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../../api/completarTrabajoApi")>();
  return {
    ...mod,
    getCompletarTrabajoDetalle: vi.fn().mockRejectedValue(new Error("offline")),
  };
});

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

const baseRow: ICompletarTrabajoPendienteRow = {
  ruta_item_id: 9,
  actuacion_id: 42,
  tipo_iniciador: "RELEVAMIENTO",
  fecha_actuacion: "2026-05-10",
  orden_trabajo_numero: "123456",
  calle: "San Martín",
  numero: "450",
  rubro_nombre: "Carnicería",
  doc_nro: "1234567",
  contrib_apellido: "Pérez",
  contrib_nombre: "Juan",
  razon_social: null,
  nombre_local: null,
  tipo_actuacion: null,
  contraproducencia: null,
  inspectores: ["García", "López"],
  inspector1: "García",
  inspector2: "López",
  inspector3: null,
};

const catalogs = {
  motivos: ["Falta de habilitación"],
  motivosComprobacion: ["Incumplimiento"],
  contraproducencias: ["No", "Sí"],
  inspectores: ["García", "López"],
  rubros: ["Carnicería"],
};

describe("CompletarTrabajoModal", () => {
  it("usa shell CRUD glass como Actuaciones", () => {
    const html = render(
      <CompletarTrabajoModal
        open
        disablePortal
        row={baseRow}
        catalogs={catalogs}
        catalogsReady
        onClose={() => undefined}
        onSuccess={() => undefined}
      />
    );
    expect(html).toContain("Completar trabajo");
    expect(html).toContain("Guardar cierre");
    expect(html).not.toContain("Cancelar");
  });

  it("no muestra Alert error inline duplicado para validación", () => {
    const html = render(
      <CompletarTrabajoModal
        open
        disablePortal
        row={baseRow}
        catalogs={catalogs}
        catalogsReady
        onClose={() => undefined}
        onSuccess={() => undefined}
      />
    );
    expect(html).not.toContain("MuiAlert-standardError");
  });
});
