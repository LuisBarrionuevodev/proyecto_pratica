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
  it("encabeza solo los datos generales del acta de comprobación", () => {
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
    expect(html).not.toContain("Estado del trámite");
    expect(html).not.toContain("Número de oficio");
    expect(html).not.toContain("Pendiente de reinspección");
    expect(html).not.toContain("Actas de la comprobación de origen");
  });

  it("muestra actas de origen existentes después del acta de comprobación", () => {
    const html = render(
      <RecorridoDetalleDocumentalDialog
        open
        disablePortal
        actuacionId={11}
        listRow={listRow}
        detalle={{
          ...detalle,
          origen_actas: {
            actuacion_origen_id: 11,
            acta_decomiso_num: "004567",
            decomiso_kilos_total: 18.5,
            acta_clausura_num: "000832",
          },
        }}
        loading={false}
        juzgados={[]}
        defaultFechaAlta="2026-07-10"
      />
    );
    expect(html).toContain("Actas de la comprobación de origen");
    expect(html).toContain("N.º acta de decomiso");
    expect(html).toContain("004567");
    expect(html).toContain("Kilos decomisados");
    expect(html).toContain("18,5 kg");
    expect(html).toContain("N.º acta de clausura");
    expect(html).toContain("000832");
    expect(html).not.toContain("Acta de decomiso ratificada");
    expect(html).not.toContain("Acta de clausura ratificada");
    const origenIdx = html.indexOf("Actas de la comprobación de origen");
    const oficioIdx = html.indexOf("Oficios");
    expect(origenIdx).toBeGreaterThan(html.indexOf("Acta de comprobación"));
    if (oficioIdx >= 0) expect(origenIdx).toBeLessThan(oficioIdx);
  });
});
