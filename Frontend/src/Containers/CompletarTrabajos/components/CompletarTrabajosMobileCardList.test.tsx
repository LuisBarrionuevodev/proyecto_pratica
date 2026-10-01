/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { ICompletarTrabajoPendienteRow } from "../../../api/completarTrabajoApi";
import { CompletarTrabajosMobileCardList } from "./CompletarTrabajosMobileCardList";

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

const sampleRow: ICompletarTrabajoPendienteRow = {
  id: 1,
  ruta_item_id: 7,
  actuacion_id: null,
  ruta_trabajo_id: 1,
  ruta_grupo_id: 1,
  iniciador_ruta_id: 1,
  grupo_nombre: "G1",
  tipo_iniciador: "RELEVAMIENTO",
  fecha_actuacion: "2026-01-01",
  orden_trabajo_numero: "555",
  iniciador_estado: "PENDIENTE",
  domicilio_texto: "Av. Siempre Viva 742",
  estado_operativo: "PENDIENTE",
  observaciones_ejecucion: null,
  calle: "Av. Siempre Viva",
  numero: "742",
  rubro_nombre: "Kiosco",
  doc_nro: null,
  contrib_apellido: null,
  contrib_nombre: null,
  razon_social: null,
  nombre_local: null,
  tipo_actuacion: null,
  contraproducencia: null,
  inspectores: [],
  inspector1: null,
  inspector2: null,
  inspector3: null,
};

describe("CompletarTrabajosMobileCardList", () => {
  it("renderiza OT, domicilio y acción Completar", () => {
    const html = render(
      <CompletarTrabajosMobileCardList
        rows={[sampleRow]}
        loading={false}
        total={1}
        page={1}
        perPage={10}
        onPageChange={vi.fn()}
        onOpenCompletarModal={vi.fn()}
      />
    );
    expect(html).toContain("OT 555");
    expect(html).toContain("Av. Siempre Viva 742");
    expect(html).toContain("Completar");
  });
});
