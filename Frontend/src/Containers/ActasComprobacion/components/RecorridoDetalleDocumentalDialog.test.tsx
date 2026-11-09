/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { IComprobacionRecorridoDetalle, IComprobacionRecorridoRow } from "../../../api/actuacionesComprobacionActasApi";
import { RecorridoDetalleDocumentalDialog } from "./RecorridoDetalleDocumentalDialog";

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
    fetchComprobacionDocumental: vi.fn().mockResolvedValue({
      comprobacion_id: 1,
      expediente_envio: { id: 1 },
    }),
    fetchOficiosByComprobacion: vi.fn().mockResolvedValue({ oficios: [] }),
    createOficioDesdeActuacion: vi.fn(),
  };
});

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

const listRow = {
  id: 11,
  fecha_actuacion: "2026-07-10",
  acta_comprobacion_num: "009345",
  orden_trabajo_numero: "123456",
  calle: "San Martín",
  numero: "450",
  inspector1: "García",
  inspector2: "López",
  estado_recorrido: "Pendiente reinspección por oficio",
  oficio_numero: "100",
  oficio_anio: 2026,
  oficios_resumen: [
    {
      oficio_texto: "100/2026",
      causa: "Control de higiene",
      numero_expediente: "12",
      anio_expediente: 2026,
      iniciador_id: 4,
      estado_iniciador: "PENDIENTE",
    },
  ],
} as IComprobacionRecorridoRow;

const detalle: IComprobacionRecorridoDetalle = {
  actuacion_id: 11,
  oficios_resumen: listRow.oficios_resumen,
  origen: { descripcion: "Actuación con acta de comprobación" },
  acta_comprobacion: { numero: "009345" },
  expediente_comprobacion_envio: { numero: "1", anio: 2026 },
  oficio: { id: 1, numero_oficio: "100", anio: 2026 },
  expediente_respuesta_oficio: null,
  reinspeccion_por_oficio: {
    iniciador_id: 4,
    estado_iniciador: "PENDIENTE",
    tipo_iniciador: "REINSPECCION_OFICIO",
  },
  resultado_final: { estado_recorrido: "Pendiente reinspección por oficio" },
  referencia_actuacion: { fecha_actuacion: "2026-07-10", acta_comprobacion_num: "009345" },
};

describe("RecorridoDetalleDocumentalDialog", () => {
  it("encabeza el acta y narra cada oficio como bloque documental", () => {
    const html = render(
      <RecorridoDetalleDocumentalDialog
        open
        disablePortal
        actuacionId={11}
        listRow={listRow}
        detalle={detalle}
        loading={false}
        juzgados={[]}
        defaultFechaAlta="2026-07-10"
      />
    );
    expect(html).toContain("Historial documental");
    expect(html).toContain("Acta N.º 009345");
    expect(html).toContain("2026-07-10");
    expect(html).toContain("OT 123456");
    expect(html).toContain("Acta de comprobación");
    expect(html).toContain("San Martín 450");
    expect(html).toContain("García");
    expect(html).toContain("Oficio 100/2026");
    expect(html).toContain("Número de oficio");
    expect(html).toContain("Control de higiene");
    expect(html).toContain("Pendiente de reinspección");
    expect(html).not.toContain("Estado del trámite");
    const iActa = html.indexOf("Acta de comprobación");
    const iOficio = html.indexOf("Oficio 100/2026");
    expect(iActa).toBeGreaterThan(-1);
    expect(iOficio).toBeGreaterThan(iActa);
  });

  it("no mezcla el cierre de oficios distintos", () => {
    const html = render(
      <RecorridoDetalleDocumentalDialog
        open
        disablePortal
        actuacionId={11}
        listRow={{
          ...listRow,
          oficios_resumen: [
            {
              oficio_texto: "432/2026",
              resultado: "CUMPLE",
              resultado_cumplimiento_oficio: "CUMPLE",
              ejecucion_reinspeccion: {
                fecha_actuacion: "2026-08-01",
                orden_trabajo_numero: "111",
                inspectores_texto: "Pérez",
              },
            },
            {
              oficio_texto: "1989/2026",
              resultado: "NO_CUMPLE",
              resultado_cumplimiento_oficio: "NO_CUMPLE",
              iniciador_id: 9,
              estado_iniciador: "PENDIENTE",
            },
          ],
        }}
        detalle={{
          ...detalle,
          oficios_resumen: [
            {
              oficio_texto: "432/2026",
              resultado: "CUMPLE",
              resultado_cumplimiento_oficio: "CUMPLE",
              ejecucion_reinspeccion: {
                fecha_actuacion: "2026-08-01",
                orden_trabajo_numero: "111",
                inspectores_texto: "Pérez",
              },
            },
            {
              oficio_texto: "1989/2026",
              resultado: "NO_CUMPLE",
              resultado_cumplimiento_oficio: "NO_CUMPLE",
              iniciador_id: 9,
              estado_iniciador: "PENDIENTE",
            },
          ],
        }}
        loading={false}
        juzgados={[]}
        defaultFechaAlta="2026-07-10"
      />
    );
    expect(html).toContain("Oficio 432/2026");
    expect(html).toContain("Oficio 1989/2026");
    expect(html).toContain("Cumple");
    expect(html).toContain("No cumple");
    const i432 = html.indexOf("Oficio 432/2026");
    const i1989 = html.indexOf("Oficio 1989/2026");
    const iCumple = html.indexOf("Cumple");
    const iNoCumple = html.indexOf("No cumple");
    expect(i432).toBeGreaterThan(-1);
    expect(i1989).toBeGreaterThan(i432);
    expect(iCumple).toBeGreaterThan(i432);
    expect(iCumple).toBeLessThan(i1989);
    expect(iNoCumple).toBeGreaterThan(i1989);
    expect(html).toContain("2026-08-01");
    expect(html).toContain("Pérez");
  });
});
