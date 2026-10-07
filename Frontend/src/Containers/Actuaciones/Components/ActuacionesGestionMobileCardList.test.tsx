/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import { ActuacionesGestionMobileCardList } from "./ActuacionesGestionMobileCardList";

const theme = createTheme();

const row: IActuacionListItem = {
  id: 1,
  orden_trabajo_numero: "100",
  fecha_actuacion: "2026-01-01",
  rubro_nombre: "Bar",
  inspector1: "A",
  inspector2: null,
  inspector3: null,
  calle: "C",
  numero: "1",
  tipo_actuacion: "Inspección",
  contraproducencia: "No",
  doc_nro: null,
  contrib_apellido: "X",
  contrib_nombre: "Y",
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
};

describe("ActuacionesGestionMobileCardList inspector", () => {
  it("muestra acciones de Mis trabajos sin Imprimir", () => {
    const html = renderToStaticMarkup(
      <ThemeProvider theme={theme}>
        <ActuacionesGestionMobileCardList
          rows={[row]}
          loading={false}
          inspectorSelfService
          onOpenDetalle={vi.fn()}
          onOpenInspectorEdit={vi.fn()}
          onOpenInspectorFotos={vi.fn()}
          onDismissInspectorRow={vi.fn()}
        />
      </ThemeProvider>
    );
    expect(html).toContain("Editar datos");
    expect(html).toContain("Cargar más fotos");
    expect(html).toContain("Eliminar de la vista Inspector");
    expect(html).not.toContain("Imprimir");
    expect(html).not.toContain("Ver / editar");
  });
});
