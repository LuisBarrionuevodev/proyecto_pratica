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
  estado_recorrido: "Pendiente reinspección por oficio",
  oficio_numero: "100",
  oficio_anio: 2026,
  oficios_resumen: [
    {
      oficio_texto: "100/2026",
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
  it("muestra Estado del trámite antes de las tarjetas de oficio", () => {
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
    expect(html).toContain("Estado del trámite");
    expect(html).toContain("Estado actual");
    expect(html).toContain("Oficio asociado");
    expect(html).toContain("Fecha de reinspección");
    expect(html).toContain("Resultado final");
    expect(html).toContain("100/2026");
  });
});
