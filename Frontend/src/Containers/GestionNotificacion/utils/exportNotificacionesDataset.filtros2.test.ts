import { beforeEach, describe, expect, it, vi } from "vitest";

const fetchAllMock = vi.fn(async () => [{ id: 1 }]);

vi.mock("../../../api/notificacionesExportApi", () => ({
  fetchAllNotificacionesForExport: (...args: unknown[]) => fetchAllMock(...args),
}));

vi.mock("./downloadNotificacionesExcel", () => ({
  downloadNotificacionesExcel: vi.fn(),
}));

vi.mock("../../../documentos/notificaciones/downloadNotificacionesListadoPdf", () => ({
  downloadNotificacionesListadoPdf: vi.fn(async () => undefined),
}));

import { exportNotificacionesDataset } from "./exportNotificacionesDataset";
import { buildHistorialNotificacionFiltroPayload } from "./buildHistorialNotificacionFiltroPayload";

const emptyForm = {
  periodMode: "month" as const,
  mes: "" as const,
  anio: "" as const,
  desde: null,
  hasta: null,
  distritoId: "" as const,
  numeroNotificacion: "",
  calleQ: "",
  contribuyenteQ: "",
  motivoId: "" as const,
  combinarConPeriodo: false,
};

describe("FILTROS-2 exportNotificacionesDataset historial", () => {
  beforeEach(() => {
    fetchAllMock.mockClear();
  });

  it("con payload mes/anio aplicado reenvía historialAppliedPayload", async () => {
    const built = buildHistorialNotificacionFiltroPayload({
      ...emptyForm,
      mes: 7,
      anio: 2026,
      distritoId: 2,
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;

    await exportNotificacionesDataset({
      format: "excel",
      desde: "2020-01-01",
      hasta: "2020-01-31",
      plazoSlice: "total",
      historialAppliedPayload: built.payload,
    });

    expect(fetchAllMock).toHaveBeenCalledWith(
      expect.objectContaining({
        plazoSlice: "total",
        historialAppliedPayload: built.payload,
      })
    );
    const call = fetchAllMock.mock.calls[0]?.[0] as {
      historialAppliedPayload?: { period: { kind: string; mes?: number; anio?: number } };
    };
    expect(call.historialAppliedPayload?.period).toEqual({ kind: "month", mes: 7, anio: 2026 });
  });

  it("búsqueda global sin período incluye omitir en payload", async () => {
    const built = buildHistorialNotificacionFiltroPayload({
      ...emptyForm,
      numeroNotificacion: "998877",
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;

    await exportNotificacionesDataset({
      format: "excel",
      desde: "2020-01-01",
      hasta: "2020-01-31",
      plazoSlice: "total",
      historialAppliedPayload: built.payload,
    });

    expect(fetchAllMock).toHaveBeenCalledWith(
      expect.objectContaining({
        historialAppliedPayload: expect.objectContaining({
          period: { kind: "global" },
          numeroNotificacion: "998877",
        }),
      })
    );
  });

  it("sin historialAppliedPayload mantiene período del diálogo", async () => {
    await exportNotificacionesDataset({
      format: "excel",
      desde: "2026-01-01",
      hasta: "2026-01-31",
      plazoSlice: "total",
    });

    expect(fetchAllMock).toHaveBeenCalledWith(
      expect.objectContaining({
        desde: "2026-01-01",
        hasta: "2026-01-31",
        historialAppliedPayload: undefined,
      })
    );
  });
});
