/** @jsxImportSource react */
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import {
  NotificacionDetalleDocumentalDialog,
  NotificacionProrrogaExpedientesCard,
  PlazosNotificacionResumenFilas,
} from "../components/NotificacionDetalleDocumentalDialog";

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
    fetchNotificacionProrrogaExpedientes: vi.fn().mockResolvedValue({ items: [] }),
  };
});

const theme = createTheme();

function render(ui: React.ReactElement) {
  return renderToStaticMarkup(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);
}

const detalleMock = {
  actuacion_id: 1,
  notificacion_id: 10,
  plazos_otorgados: 2,
  plazo_notificacion: {
    plazo_legal_dias: 5,
    prorroga_total_dias: 15,
    fecha_notificacion: "2026-06-01",
    fecha_vencimiento: "2026-07-20",
  },
  items: [
    {
      id: 1,
      numero_expediente: "969717",
      anio: "2026",
      fecha_expediente: "2026-06-04",
      created_at: null,
      tipo_expediente: "PRORROGA_NOTIFICACION",
      plazo_otorgado: 10,
    },
  ],
  edicion: {
    puede_editar_expediente_prorroga: true,
    motivos_bloqueo_expediente: [],
  },
};

const baseRow = {
  id: 1,
  acta_notificacion_num: "000000",
  fecha_actuacion: "2026-06-01",
  dias_restantes: 15,
  source_type: "NOTIFICACION",
  calle: "San Martín",
  numero: "100",
} as IActuacionesPendientesItem;

const dialogProps = {
  open: true,
  disablePortal: true,
  expNumero: "",
  onExpNumeroChange: () => undefined,
  expFecha: "",
  onExpFechaChange: () => undefined,
  prorrogaDias: "0",
  onProrrogaDiasChange: () => undefined,
  fieldErrors: {},
  modalApiError: null,
  saving: false,
  onGuardar: async () => ({ ok: true, volvioEnPlazo: false }),
  onClose: () => undefined,
};

describe("NotificacionDetalleDocumentalDialog", () => {
  it("header limpio: chip, título y solo número de acta en subtítulo", () => {
    const html = render(
      <NotificacionDetalleDocumentalDialog
        {...dialogProps}
        row={baseRow}
        variant="documental"
        esReinspeccionNotificacion
      />
    );
    expect(html).toContain("Notificación");
    expect(html).toContain("Notificación detalle");
    expect(html).toContain("Número de acta de notificación N.º 000000");
    expect(html).not.toContain("Estado:");
    expect(html).not.toContain("Fecha: 2026-06-01");
    expect(html).not.toContain("15 días restantes");
  });

  it("modo prórroga operativo usa mismo header limpio", () => {
    const html = render(
      <NotificacionDetalleDocumentalDialog
        {...dialogProps}
        row={baseRow}
        variant="soloExpediente"
        esReinspeccionNotificacion
      />
    );
    expect(html).toContain("Notificación detalle");
    expect(html).toContain("Número de acta de notificación N.º 000000");
    expect(html).not.toContain("Fecha de actuación");
    expect(html).toContain("Alta de expediente de prórroga");
    expect(html).not.toContain(">Prórroga<");
  });

  it("historial relata las cuatro etapas con fecha de origen", () => {
    const html = render(
      <NotificacionDetalleDocumentalDialog {...dialogProps} row={baseRow} variant="documental" />
    );
    expect(html).toContain("Inspección de origen");
    expect(html).toContain("Fecha de actuación");
    expect(html).toContain("2026-06-01");
    expect(html).toContain("Motivos de notificación");
    expect(html).toContain("Plazos y prórrogas");
    expect(html).toContain("Reinspección y cierre");
    expect(html.indexOf("Inspección de origen")).toBeLessThan(html.indexOf("Motivos de notificación"));
    expect(html.indexOf("Motivos de notificación")).toBeLessThan(html.indexOf("Plazos y prórrogas"));
    expect(html.indexOf("Plazos y prórrogas")).toBeLessThan(html.indexOf("Reinspección y cierre"));
    expect(html).not.toContain("La visita");
    expect(html).not.toContain("Cierre de la notificación");
    expect(html).not.toContain("segunda inspección");
  });

  it("Reinspección y cierre no duplica faltas no subsanadas y muestra motivo", () => {
    const html = render(
      <NotificacionDetalleDocumentalDialog
        {...dialogProps}
        row={{
          ...baseRow,
          seguimiento_notificacion: {
            estado: "FALTAS_NO_SUBSANADAS",
            actuacion_id: 8,
            fecha_reinspeccion: "2026-04-10",
            orden_trabajo_numero: "OT99",
            acta_inspeccion_num: "654321",
            acta_comprobacion_num: "REIN02",
            comprobacion_motivo: "Higiene del local",
            inspectores_texto: "Pérez",
            faltas_subsanadas: false,
          },
        }}
        variant="documental"
      />
    );
    expect(html).toContain("Reinspección y cierre");
    expect(html).toContain("Faltas no subsanadas");
    expect(html).toContain("Motivos de comprobación");
    expect(html).toContain("Higiene del local");
    expect(html).toContain("Acta de inspección N.º");
    expect(html).toContain("OT99");
    expect(html).not.toContain("Resultado de las faltas");
  });

  it("histórico incompleto muestra resultado no informado", () => {
    const html = render(
      <NotificacionDetalleDocumentalDialog
        {...dialogProps}
        row={{
          ...baseRow,
          seguimiento_notificacion: {
            estado: "REINSPECCION_REALIZADA_SIN_RESULTADO",
            actuacion_id: 8,
            fecha_reinspeccion: "2026-04-10",
            acta_comprobacion_num: "REIN03",
            inspectores_texto: "Pérez",
            faltas_subsanadas: null,
          },
        }}
        variant="documental"
      />
    );
    expect(html).toContain("Reinspección realizada · resultado no informado");
    expect(html).toContain("No informado");
    expect(html).toContain("Motivos de comprobación");
    expect(html).not.toContain("Faltas subsanadas");
  });
});

describe("PlazosNotificacionResumenFilas", () => {
  it("muestra plazos sin expediente en actas ni contador de expedientes", () => {
    const html = render(
      <PlazosNotificacionResumenFilas detalle={detalleMock} diasRestantes="15 días" />
    );
    expect(html).toContain("Fecha de notificación");
    expect(html).toContain("2026-06-01");
    expect(html).toContain("Vencimiento");
    expect(html).toContain("2026-07-20");
    expect(html).toContain("Días restantes");
    expect(html).toContain("Plazo legal (días hábiles)");
    expect(html).toContain("Prórroga total (días)");
    expect(html).not.toContain("Expediente en actas");
    expect(html).not.toContain("Plazos otorgados");
  });
});

describe("NotificacionProrrogaExpedientesCard", () => {
  it("lista expedientes abajo sin fila resumen de cantidad", () => {
    const html = render(
      <NotificacionProrrogaExpedientesCard
        loading={false}
        error={null}
        detalle={detalleMock}
        actuacionId={1}
        diasRestantes="15 días"
      />
    );
    expect(html).toContain("Expedientes de prórroga");
    expect(html).toContain("969717");
    expect(html).toContain("Plazo otorgado");
    expect(html).not.toContain("Expediente en actas");
  });
});
