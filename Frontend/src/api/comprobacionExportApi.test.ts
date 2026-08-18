import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./actuacionesComprobacionActasApi", () => ({
  fetchComprobacionRecorrido: vi.fn(async () => ({
    items: [],
    meta: { total: 0, desde: null, hasta: null },
  })),
  fetchComprobacionPendientesOficio: vi.fn(),
  fetchPendientesReinspeccionOficio: vi.fn(),
}));

vi.mock("./actuacionesPendientesApi", () => ({
  getActuacionesPendientesExpediente: vi.fn(),
}));

import { fetchComprobacionRecorrido } from "./actuacionesComprobacionActasApi";
import { fetchAllComprobacionesForExport } from "./comprobacionExportApi";

describe("FILTROS-1 fetchAllComprobacionesForExport recorrido", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("prioriza recorridoApiParams y reenvía expediente_numero", async () => {
    await fetchAllComprobacionesForExport({
      slice: "recorrido",
      desde: "2020-01-01",
      hasta: "2020-01-31",
      recorridoApiParams: {
        expediente_numero: "789",
        omitirRangoFecha: true,
      },
    });

    expect(fetchComprobacionRecorrido).toHaveBeenCalledWith({
      expediente_numero: "789",
      omitirRangoFecha: true,
    });
    expect(fetchComprobacionRecorrido).not.toHaveBeenCalledWith(
      expect.objectContaining({ desde: "2020-01-01" })
    );
  });

  it("recorridoApiParams con mes/anio no fuerza desde/hasta del diálogo", async () => {
    await fetchAllComprobacionesForExport({
      slice: "recorrido",
      desde: "2025-01-01",
      hasta: "2025-01-31",
      recorridoApiParams: {
        mes: 4,
        anio: 2024,
        distrito_id: 2,
      },
    });

    expect(fetchComprobacionRecorrido).toHaveBeenCalledWith({
      mes: 4,
      anio: 2024,
      distrito_id: 2,
    });
  });

  it("sin recorridoApiParams usa fallback documental incluyendo expediente", async () => {
    await fetchAllComprobacionesForExport({
      slice: "recorrido",
      desde: "2026-03-01",
      hasta: "2026-03-31",
      expedienteNumero: "66234",
      oficioNumero: "88",
      actaComprobacion: "123",
      calleQ: "San Martín",
      contribuyenteQ: "Pérez",
      tipoFinal: "CUMPLE",
      distritoId: 3,
    });

    expect(fetchComprobacionRecorrido).toHaveBeenCalledWith({
      desde: "2026-03-01",
      hasta: "2026-03-31",
      distrito_id: 3,
      contrib_q: "Pérez",
      calle_q: "San Martín",
      acta_comprobacion: "123",
      oficio_numero: "88",
      expediente_numero: "66234",
      tipo_final: "CUMPLE",
    });
  });
});
