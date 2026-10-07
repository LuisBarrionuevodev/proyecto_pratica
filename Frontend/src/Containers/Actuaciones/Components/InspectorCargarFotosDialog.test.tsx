/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { InspectorCargarFotosDialog } from "./InspectorCargarFotosDialog";

vi.mock("../../../features/media/components/ActuacionMediaGallery", () => ({
  ActuacionMediaGallery: () => <div data-testid="gallery-stub">Galería</div>,
}));

vi.mock("../../../components/feedback", () => ({
  useAppFeedback: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  }),
}));

const theme = createTheme();

const draft: IActuacionListItem = {
  id: 9,
  orden_trabajo_numero: "555",
  fecha_actuacion: "2026-02-01",
  rubro_nombre: null,
  inspector1: null,
  inspector2: null,
  inspector3: null,
  calle: null,
  numero: null,
  tipo_actuacion: null,
  contraproducencia: null,
  doc_nro: null,
  contrib_apellido: null,
  contrib_nombre: null,
  acta_inspeccion_num: null,
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
  ruta_item_id: 77,
};

describe("InspectorCargarFotosDialog", () => {
  it("expone GUARDAR FOTOS y título de solo fotos", () => {
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <InspectorCargarFotosDialog
          open
          disablePortal
          draft={draft}
          onClose={() => undefined}
        />
      </ThemeProvider>
    );
    expect(html).toContain("GUARDAR FOTOS");
    expect(html).toContain("Cargar más fotos");
    expect(html).not.toContain("Editar actuación");
  });
});
