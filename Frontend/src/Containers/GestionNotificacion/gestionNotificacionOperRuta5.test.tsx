import { describe, expect, it, vi, beforeEach } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { puedeAgregarARutaDeTrabajo } from "../../utils/operRutaPoolAcciones";
import { createRutaPoolDia } from "../../api/rutaPoolDiaApi";

vi.mock("../../api/rutaPoolDiaApi", () => ({
  createRutaPoolDia: vi.fn(),
  listRutaPoolDia: vi.fn(),
  agregarDesdePoolRuta: vi.fn(),
}));

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

describe("GestionNotificacion OPER-RUTA.5/6", () => {
  const page = read("src/Containers/GestionNotificacion/GestionNotificacionPage.tsx");
  const cell = read("src/components/operRuta/OperRutaPoolAccionesCell.tsx");

  it("Pendiente reinspección integra OperRutaPoolAccionesCell", () => {
    expect(page).toContain("OperRutaPoolAccionesCell");
    expect(page).toContain("columnsReinspeccionOperativa");
    expect(cell).toContain("OPER_RUTA_LABELS.GESTIONAR_EN_RUTA");
  });

  it("en plazo / por vencer no integran acciones pool en columnas operativas", () => {
    const operativaBlock = page.split("const columnsOperativa")[1]?.split("const columnsHistorial")[0] ?? "";
    expect(operativaBlock).not.toContain("OperRutaPoolAccionesCell");
  });

  it("Historial no integra acciones pool", () => {
    const historialBlock = page.split("const columnsHistorial")[1]?.split("const columnsReinspeccionOperativa")[0] ?? "";
    expect(historialBlock).not.toContain("OperRutaPoolAccionesCell");
  });

  it("pendiente y en_pool habilitan agregar a ruta de trabajo", () => {
    expect(puedeAgregarARutaDeTrabajo({ iniciador_id: 1, estado_operativo_pool: "pendiente" })).toBe(true);
    expect(puedeAgregarARutaDeTrabajo({ iniciador_id: 1, estado_operativo_pool: "en_pool" })).toBe(true);
  });

  it("en_ruta_borrador no muestra acciones inválidas", () => {
    expect(puedeAgregarARutaDeTrabajo({ iniciador_id: 1, estado_operativo_pool: "en_ruta_borrador" })).toBe(false);
  });
});

describe("createRutaPoolDia API", () => {
  beforeEach(() => {
    vi.mocked(createRutaPoolDia).mockResolvedValue({
      item: { pool_id: 9, iniciador_id: 301, iniciador_ruta_id: 301, estado: "EN_POOL", fecha: "2026-05-01" },
    });
  });

  it("envía iniciador_ruta_id y fecha", async () => {
    await createRutaPoolDia({
      origen_tipo: "INICIADOR",
      iniciador_ruta_id: 301,
      fecha: "2026-05-01",
    });
    expect(createRutaPoolDia).toHaveBeenCalledWith({
      origen_tipo: "INICIADOR",
      iniciador_ruta_id: 301,
      fecha: "2026-05-01",
    });
  });
});
