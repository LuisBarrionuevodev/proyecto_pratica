import { describe, expect, it } from "vitest";

import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import {
  normalizeRelevamientoRowForApi,
  RELEVAMIENTO_ROW_ERROR_KEY_MAP,
} from "./submitRelevamientoRow";

describe("submitRelevamientoRow — payload domicilio", () => {
  const baseRow: IRelevamientoListItem = {
    id: 42,
    fecha: "2026-06-02",
    inspector: "Inspector Uno",
    calle: "TestRelevamientoDomicilio_abc",
    numero: "123",
    rubro: "Panadería",
    turno: "MANIANA",
    esta_abierto: true,
  };

  it("normaliza fila conservando calle y número", () => {
    const normalized = normalizeRelevamientoRowForApi(baseRow);
    expect(normalized.calle).toBe("TestRelevamientoDomicilio_abc");
    expect(normalized.numero).toBe("123");
    expect(normalized.inspector).toBe("Inspector Uno");
    expect(normalized.rubro).toBe("Panadería");
  });

  it("mapea errores de grid a claves de domicilio", () => {
    expect(RELEVAMIENTO_ROW_ERROR_KEY_MAP.Calle).toBe("calle");
    expect(RELEVAMIENTO_ROW_ERROR_KEY_MAP.Numero).toBe("numero");
    expect(RELEVAMIENTO_ROW_ERROR_KEY_MAP._row).toBe("calle");
  });

  it("no vacía calle/número al normalizar esta_abierto", () => {
    const normalized = normalizeRelevamientoRowForApi({
      ...baseRow,
      esta_abierto: "Sí" as unknown as boolean,
    });
    expect(normalized.calle).toBeTruthy();
    expect(normalized.numero).toBeTruthy();
    expect(normalized.esta_abierto).toBe(true);
  });
});
