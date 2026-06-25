import { describe, expect, it } from "vitest";

import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import {
  relevamientoCalleDisplay,
  relevamientoEstaAbiertoDisplay,
  relevamientoNumeroDisplay,
  relevamientoTurnoDisplay,
} from "./relevamientoCrudDisplay";

const baseRow: IRelevamientoListItem = {
  id: 42,
  fecha: "2026-05-01",
  inspector: "Pérez",
  calle: "Raw Calle",
  numero: "123",
  rubro: "Panadería",
  turno: "MANIANA",
  esta_abierto: true,
  domicilio_id: 99,
};

describe("relevamientoCrudDisplay", () => {
  it("muestra calle normalizada cuando calle_estado es OK", () => {
    expect(
      relevamientoCalleDisplay({
        ...baseRow,
        calle_estado: "OK",
        calle_normalizada: "Calle Canónica",
      })
    ).toBe("Calle Canónica");
  });

  it("muestra esquina en ficha cuando numero_tipo es ESQUINA", () => {
    expect(
      relevamientoNumeroDisplay({
        ...baseRow,
        numero_tipo: "ESQUINA",
        numero_esquina: "Calle A y Calle B",
      })
    ).toBe("Calle A y Calle B");
  });

  it("formatea turno y está abierto", () => {
    expect(relevamientoTurnoDisplay("TARDE")).toBe("Tarde");
    expect(relevamientoEstaAbiertoDisplay(true)).toBe("Sí");
    expect(relevamientoEstaAbiertoDisplay(null)).toBe("—");
  });
});

describe("normalizeRelevamientoRowForApi domicilio", () => {
  it("conserva domicilio_id en payload de fila", async () => {
    const { normalizeRelevamientoRowForApi } = await import("./submitRelevamientoRow");
    const normalized = normalizeRelevamientoRowForApi(baseRow);
    expect(normalized.domicilio_id).toBe(99);
    expect(normalized.calle).toBe("Raw Calle");
  });
});
