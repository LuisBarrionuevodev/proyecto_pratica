import { describe, expect, it } from "vitest";

import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import {
  buildRelevamientoGridRow,
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

  it("mapea errores de grid a claves de domicilio y campos PR7.4", () => {
    expect(RELEVAMIENTO_ROW_ERROR_KEY_MAP.Calle).toBe("calle");
    expect(RELEVAMIENTO_ROW_ERROR_KEY_MAP.Numero).toBe("numero");
    expect(RELEVAMIENTO_ROW_ERROR_KEY_MAP._row).toBe("calle");
    expect(RELEVAMIENTO_ROW_ERROR_KEY_MAP["Nombre fantasía"]).toBe("nombre_fantasia");
    expect(RELEVAMIENTO_ROW_ERROR_KEY_MAP["Ángulo esquina"]).toBe("angulo_esquina");
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

  it("payload grid incluye nombre_fantasia y angulo_esquina", () => {
    const grid = buildRelevamientoGridRow({
      ...baseRow,
      numero_tipo: "ESQUINA",
      numero: "Belgrano y Mitre",
      nombre_fantasia: "El Toro",
      angulo_esquina: "NE",
    });
    expect(grid["Nombre fantasía"]).toBe("El Toro");
    expect(grid["Ángulo esquina"]).toBe("NE");
  });

  it("string vacío de nombre fantasía se envía como null en API", () => {
    const normalized = normalizeRelevamientoRowForApi({
      ...baseRow,
      nombre_fantasia: "   ",
      angulo_esquina: "",
    });
    expect(normalized.nombre_fantasia).toBeNull();
    expect(normalized.angulo_esquina).toBeNull();
  });

  it("ángulo en domicilio NUMERO se normaliza a null", () => {
    const normalized = normalizeRelevamientoRowForApi({
      ...baseRow,
      numero_tipo: "NUMERO",
      angulo_esquina: "NE",
    });
    expect(normalized.angulo_esquina).toBeNull();
  });
});
