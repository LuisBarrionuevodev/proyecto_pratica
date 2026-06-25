/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { fetchCallesCatalogo } from "../../../api/geolocalizacionApi";
import { ActuacionDetalleDialog } from "./ActuacionDetalleDialog";

vi.mock("../../../components/feedback", () => ({
  useAppFeedback: () => ({
    warning: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

vi.mock("../../../api/geolocalizacionApi", () => ({
  fetchCallesCatalogo: vi.fn(),
}));

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(
    <MemoryRouter>
      <ThemeProvider theme={theme}>{ui}</ThemeProvider>
    </MemoryRouter>
  );
}

const baseRow: IActuacionListItem = {
  id: 42,
  orden_trabajo_numero: "12345",
  fecha_actuacion: "2026-05-10",
  rubro_nombre: "Carnicería",
  inspector1: "García",
  inspector2: "López",
  inspector3: null,
  calle: "San Martín",
  numero: "450",
  numero_tipo: "NUMERO",
  tipo_actuacion: "Inspección",
  contraproducencia: "No",
  doc_nro: "30123456",
  contrib_apellido: "Pérez",
  contrib_nombre: "Juan",
  acta_inspeccion_num: "100",
  acta_notificacion_num: null,
  notificacion_motivo_1: null,
  notificacion_motivo_2: null,
  notificacion_motivo_3: null,
  acta_comprobacion_num: null,
  comprobacion_motivo: null,
  acta_clausura_num: null,
  acta_decomiso_num: null,
  decomiso_kilos_total: null,
  expediente_numero: null,
  expediente_anio: null,
  oficio_numero: null,
  oficio_anio: null,
  oficio_causa: null,
};

const catalogs = {
  inspectores: ["García", "López"],
  motivos: ["Falta de habilitación"],
  rubros: ["Carnicería"],
  tipos: ["Inspección"],
  contraproducencias: ["No", "Sí"],
  motivosComprobacion: ["Incumplimiento"],
};

describe("ActuacionDetalleDialog domicilio sin catálogo", () => {
  it("calle es input libre y no usa Autocomplete de calles", () => {
    vi.mocked(fetchCallesCatalogo).mockClear();
    const html = render(
      <ActuacionDetalleDialog
        open
        disablePortal
        initialEditing
        draft={baseRow}
        fieldErrors={{}}
        saving={false}
        catalogs={catalogs}
        readOnlyColumns={[]}
        onClose={() => undefined}
        onDraftChange={() => undefined}
        onSave={() => undefined}
      />
    );
    expect(html).toContain("Calle");
    expect(html).toContain("Esquina");
    expect(html).toContain("Número o referencia");
    expect(fetchCallesCatalogo).not.toHaveBeenCalled();
  });
});
