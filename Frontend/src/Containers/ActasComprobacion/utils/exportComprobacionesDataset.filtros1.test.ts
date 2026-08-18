import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchAllMock = vi.fn(async () => [{ id: 1 }]);

vi.mock("../../../api/comprobacionExportApi", () => ({
  fetchAllComprobacionesForExport: (...args: unknown[]) => fetchAllMock(...args),
}));

vi.mock("./downloadComprobacionesExcel", () => ({
  downloadComprobacionesExcel: vi.fn(),
}));

vi.mock("../../../documentos/comprobaciones/downloadComprobacionesListadoPdf", () => ({
  downloadComprobacionesListadoPdf: vi.fn(async () => undefined),
}));

import { exportComprobacionesDataset } from "./exportComprobacionesDataset";
import { buildRecorridoComprobacionFiltroPayload } from "./buildRecorridoComprobacionFiltroPayload";

describe("FILTROS-1 exportComprobacionesDataset recorrido", () => {
  beforeEach(() => {
    fetchAllMock.mockClear();
  });

  it("con payload mes/anio aplicado reenvía mes y anio sin desde/hasta del diálogo", async () => {
    const built = buildRecorridoComprobacionFiltroPayload({
      periodMode: "month",
      mes: 7,
      anio: 2026,
      desde: null,
      hasta: null,
      distritoId: 2,
      actaComprobacion: "",
      calleQ: "",
      contribuyenteQ: "",
      oficioNumero: "",
      expedienteNumero: "",
      tipoFinal: "",
      combinarConPeriodo: false,
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;

    await exportComprobacionesDataset({
      format: "excel",
      desde: "2020-01-01",
      hasta: "2020-01-31",
      slice: "recorrido",
      recorridoAppliedPayload: built.payload,
    });

    expect(fetchAllMock).toHaveBeenCalledWith(
      expect.objectContaining({
        slice: "recorrido",
        recorridoApiParams: expect.objectContaining({
          mes: 7,
          anio: 2026,
          distrito_id: 2,
        }),
      })
    );
    const call = fetchAllMock.mock.calls[0]?.[0] as {
      recorridoApiParams?: { omitirRangoFecha?: boolean; desde?: string };
    };
    expect(call.recorridoApiParams?.omitirRangoFecha).toBeUndefined();
    expect(call.recorridoApiParams?.desde).toBeUndefined();
  });

  it("combina período con búsqueda específica cuando el usuario lo pidió", async () => {
    const built = buildRecorridoComprobacionFiltroPayload({
      periodMode: "month",
      mes: 7,
      anio: 2026,
      desde: null,
      hasta: null,
      distritoId: "",
      actaComprobacion: "",
      calleQ: "",
      contribuyenteQ: "",
      oficioNumero: "45",
      expedienteNumero: "789",
      tipoFinal: "",
      combinarConPeriodo: true,
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;

    await exportComprobacionesDataset({
      format: "excel",
      desde: "2020-01-01",
      hasta: "2020-01-31",
      slice: "recorrido",
      recorridoAppliedPayload: built.payload,
    });

    expect(fetchAllMock).toHaveBeenCalledWith(
      expect.objectContaining({
        recorridoApiParams: expect.objectContaining({
          mes: 7,
          anio: 2026,
          oficio_numero: "45",
          expediente_numero: "789",
        }),
      })
    );
  });

  it("búsqueda global sin período exporta con omitir_rango_fecha", async () => {
    const built = buildRecorridoComprobacionFiltroPayload({
      periodMode: "month",
      mes: "",
      anio: "",
      desde: null,
      hasta: null,
      distritoId: "",
      actaComprobacion: "",
      calleQ: "",
      contribuyenteQ: "",
      oficioNumero: "",
      expedienteNumero: "100200",
      tipoFinal: "",
      combinarConPeriodo: false,
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;

    await exportComprobacionesDataset({
      format: "excel",
      desde: "2020-01-01",
      hasta: "2020-01-31",
      slice: "recorrido",
      recorridoAppliedPayload: built.payload,
    });

    expect(fetchAllMock).toHaveBeenCalledWith(
      expect.objectContaining({
        recorridoApiParams: expect.objectContaining({
          expediente_numero: "100200",
          omitirRangoFecha: true,
        }),
      })
    );
  });

  it("rango desde/hasta aplicado se reenvía en recorridoApiParams", async () => {
    const built = buildRecorridoComprobacionFiltroPayload({
      periodMode: "range",
      mes: "",
      anio: "",
      desde: "2026-01-10",
      hasta: "2026-01-20",
      distritoId: "",
      actaComprobacion: "",
      calleQ: "",
      contribuyenteQ: "",
      oficioNumero: "",
      expedienteNumero: "",
      tipoFinal: "",
      combinarConPeriodo: false,
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;

    await exportComprobacionesDataset({
      format: "excel",
      desde: "2020-01-01",
      hasta: "2020-01-31",
      slice: "recorrido",
      recorridoAppliedPayload: built.payload,
    });

    expect(fetchAllMock).toHaveBeenCalledWith(
      expect.objectContaining({
        recorridoApiParams: expect.objectContaining({
          desde: "2026-01-10",
          hasta: "2026-01-20",
        }),
      })
    );
  });
});
