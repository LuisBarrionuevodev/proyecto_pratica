/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { IComprobacionDocumentalResponse, OficioComprobacionItem } from "../../../api/actuacionesPendientesApi";
import { ComprobacionOficiosTribunalSection } from "./ComprobacionOficiosTribunalSection";
import { OperativoOficioYRespuestaEditable } from "./ComprobacionOficioOperativoDialog";

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

const edicion: IComprobacionDocumentalResponse["edicion"] = {
  comprobacion_usada_como_iniciador: true,
  puede_editar_expediente_envio: false,
  puede_editar_bloque_oficio: false,
  puede_eliminar_expediente_envio: false,
  puede_eliminar_bloque_oficio: false,
  motivos_bloqueo_expediente_envio: [],
  motivos_bloqueo_oficio: ["Iniciador en estado CUMPLIDO."],
  motivos_bloqueo_eliminar_expediente_envio: [],
  motivos_bloqueo_eliminar_bloque_oficio: [],
};

const documental: IComprobacionDocumentalResponse = {
  actuacion_id: 11,
  comprobacion_id: 1,
  expediente_envio: {
    id: 1,
    numero_expediente: "1",
    anio: "2026",
    fecha_expediente: "2026-07-01",
    tipo_expediente: "ENVIO_ACTA",
    oficio_id: null,
  },
  oficio: null,
  expediente_respuesta: null,
  edicion,
};

const sectionProps = {
  open: true,
  actuacionId: 11,
  documental,
  documentalLoading: false,
  oficiosLoading: false,
  oficiosError: null,
  juzgados: [] as { id: number; nombre: string }[],
  defaultFechaAlta: "2026-07-10",
  modalApiError: null,
  saving: false,
  onGuardarAlta: async () => undefined,
  onDocumentalUpdated: async () => undefined,
};

function countLabel(html: string, label: string): number {
  const re = new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g");
  return html.match(re)?.length ?? 0;
}

describe("ComprobacionOficiosTribunalSection cierre documental", () => {
  it("un oficio cumplido muestra Cumple una sola vez y no Cumplido", () => {
    const oficios: OficioComprobacionItem[] = [
      {
        id: 350,
        numero_oficio: "350",
        anio: 2026,
        expediente_id: 88,
        expediente_numero: "013151",
        expediente_anio: 2026,
        causa: "Higiene",
        tribunal: "Juzgado 1",
        estado_operativo: "cumplido",
        iniciador_estado: "CUMPLIDO",
        resultado_cumplimiento_oficio: "CUMPLE",
        editable: false,
        bloqueado_motivo: "Iniciador en estado CUMPLIDO.",
        ejecucion_reinspeccion: {
          fecha_actuacion: "2026-08-01",
          orden_trabajo_numero: "111",
          inspectores_texto: "Pérez",
          resultado_cumplimiento_oficio: "CUMPLE",
        },
      },
    ];
    const html = render(
      <ComprobacionOficiosTribunalSection
        {...sectionProps}
        oficios={oficios}
        cierreUnicoEnEncabezado
      />
    );
    expect(html).toContain("Oficio 350/2026 · Exp. 013151/2026");
    expect(html).toContain("Cumple");
    expect(html).toContain("Edición bloqueada");
    expect(html).toContain("Pérez");
    expect(html).toContain("2026-08-01");
    expect(html).toContain("Agregar otro oficio");
    expect(html).not.toContain("Cumplido");
    expect(html).not.toContain("Cumplimiento");
    expect(countLabel(html, "Cumple")).toBe(1);
  });

  it("oficio pendiente no muestra datos de reinspección", () => {
    const oficios: OficioComprobacionItem[] = [
      {
        id: 100,
        numero_oficio: "100",
        anio: 2026,
        expediente_numero: "12",
        expediente_anio: 2026,
        causa: "Control de higiene",
        tribunal: "Juzgado 1",
        iniciador_id: 4,
        iniciador_estado: "PENDIENTE",
        estado_operativo: "pendiente",
      },
    ];
    const html = render(
      <ComprobacionOficiosTribunalSection
        {...sectionProps}
        oficios={oficios}
        cierreUnicoEnEncabezado
      />
    );
    expect(html).toContain("Pendiente de reinspección");
    expect(html).not.toContain("Resultado de la reinspección");
    expect(html).not.toContain("Cumple");
    expect(html).toContain("Agregar otro oficio");
  });

  it("dos oficios conservan su propio cierre", () => {
    const oficios: OficioComprobacionItem[] = [
      {
        id: 432,
        numero_oficio: "432",
        anio: 2026,
        expediente_numero: "1",
        expediente_anio: 2026,
        resultado_cumplimiento_oficio: "CUMPLE",
        estado_operativo: "cumplido",
        ejecucion_reinspeccion: {
          fecha_actuacion: "2026-08-01",
          inspectores_texto: "Pérez",
        },
      },
      {
        id: 1989,
        numero_oficio: "1989",
        anio: 2026,
        expediente_numero: "2",
        expediente_anio: 2026,
        resultado_cumplimiento_oficio: "NO_CUMPLE",
        iniciador_id: 9,
        iniciador_estado: "PENDIENTE",
      },
    ];
    const html = render(
      <ComprobacionOficiosTribunalSection
        {...sectionProps}
        oficios={oficios}
        cierreUnicoEnEncabezado
      />
    );
    expect(html).toContain("Oficio 432/2026");
    expect(html).toContain("Oficio 1989/2026");
    const i432 = html.indexOf("Oficio 432/2026");
    const i1989 = html.indexOf("Oficio 1989/2026");
    const iCumple = html.indexOf("Cumple");
    const iNoCumple = html.indexOf("No cumple");
    expect(iCumple).toBeGreaterThan(i432);
    expect(iCumple).toBeLessThan(i1989);
    expect(iNoCumple).toBeGreaterThan(i1989);
    const sliceCumple = html.slice(i432, i1989);
    const sliceNo = html.slice(i1989);
    expect(sliceCumple).toContain("Pérez");
    expect(sliceNo).not.toContain("Pérez");
    expect(html).toContain("Agregar otro oficio");
  });

  it("sin cierre único conserva Cumplimiento en la reinspección", () => {
    const oficios: OficioComprobacionItem[] = [
      {
        id: 350,
        numero_oficio: "350",
        anio: 2026,
        resultado_cumplimiento_oficio: "CUMPLE",
        estado_operativo: "cumplido",
        ejecucion_reinspeccion: {
          fecha_actuacion: "2026-08-01",
          resultado_cumplimiento_oficio: "CUMPLE",
        },
      },
    ];
    const html = render(
      <ComprobacionOficiosTribunalSection {...sectionProps} oficios={oficios} />
    );
    expect(html).toContain("Cumplido");
    expect(html).toContain("Cumplimiento");
  });
});

describe("OperativoOficioYRespuestaEditable motivo de bloqueo", () => {
  const doc: IComprobacionDocumentalResponse = {
    actuacion_id: 11,
    comprobacion_id: 1,
    expediente_envio: documental.expediente_envio,
    oficio: {
      id: 350,
      numero_oficio: "350",
      anio: 2026,
      fecha_oficio: "2026-07-02",
      causa: "Higiene",
      juzgado_id: 1,
      juzgado_nombre: "Juzgado 1",
    },
    expediente_respuesta: {
      id: 88,
      numero_expediente: "013151",
      anio: "2026",
      fecha_expediente: "2026-07-02",
      tipo_expediente: "RESPUESTA_OFICIO",
      oficio_id: 350,
    },
    edicion,
  };

  it("oculta el motivo técnico cuando el encabezado ya muestra Edición bloqueada", () => {
    const html = render(
      <OperativoOficioYRespuestaEditable
        open
        actuacionId={11}
        documental={doc}
        juzgados={[]}
        onDocumentalUpdated={async () => undefined}
        oficioEditable={false}
        bloqueadoMotivo="Iniciador en estado CUMPLIDO."
        embedEnCard
        ocultarMotivoBloqueo
      />
    );
    expect(html).not.toContain("CUMPLIDO");
    expect(html).not.toContain("Cumplido");
    expect(html).not.toContain("No editable");
  });
});
