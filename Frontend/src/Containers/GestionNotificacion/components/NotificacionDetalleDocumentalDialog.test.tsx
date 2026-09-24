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

  it("historial no muestra Fecha de actuación duplicada", () => {
    const html = render(
      <NotificacionDetalleDocumentalDialog {...dialogProps} row={baseRow} variant="documental" />
    );
    expect(html).not.toContain("Fecha de actuación");
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
