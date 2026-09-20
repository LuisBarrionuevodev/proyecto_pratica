import { describe, expect, it } from "vitest";

import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import {
  applyRelevamientoDomicilioSubmitGuard,
  buildRelevamientoGridRow,
  buildRelevamientoUpdatePayload,
  normalizeRelevamientoRowForApi,
  RELEVAMIENTO_ROW_ERROR_KEY_MAP,
} from "./submitRelevamientoRow";
import { relevamientoRowParaEdicion } from "./relevamientoCamposForm";

describe("submitRelevamientoRow — payload domicilio", () => {
  const baseRow: IRelevamientoListItem = {
    id: 42,
    fecha: "2026-06-02",
    relevadores_label: "Fabian Esquivel",
    relevador_ids: [1],
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
    expect(normalized.relevador_ids).toEqual([1]);
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

  it("submit guard usa calle normalizada si draft no editó", () => {
    const baseline = {
      ...baseRow,
      calle: "San Martín",
      calle_estado: "OK",
      calle_normalizada: "Av. San Martín",
    };
    const hydrated = relevamientoRowParaEdicion(baseline);
    const payload = applyRelevamientoDomicilioSubmitGuard(hydrated, baseline);
    expect(payload.calle).toBe("Av. San Martín");
    expect(payload.numero).toBe("123");
    expect(payload.calle_normalizada).toBeUndefined();
  });

  it("submit guard envía calle editada, no la baseline", () => {
    const baseline = {
      ...baseRow,
      calle: "Maipú",
      calle_normalizada: "Maipú",
    };
    const draft = { ...relevamientoRowParaEdicion(baseline), calle: "Mendoza" };
    const payload = applyRelevamientoDomicilioSubmitGuard(draft, baseline);
    expect(payload.calle).toBe("Mendoza");
  });

  it("REL-MAP-CIERRE.2-3: grid row no incluye Fecha (paridad batch)", () => {
    const grid = buildRelevamientoGridRow(baseRow);
    expect(grid).not.toHaveProperty("Fecha");
    expect(grid.Relevador).toBe("Fabian Esquivel");
  });

  it("REL-MAP-CIERRE.2-3: PUT payload explícito sin fecha ni relevadores DTO", () => {
    const payload = buildRelevamientoUpdatePayload({
      ...baseRow,
      relevadores: [{ id: 1, nombre: "Fabian Esquivel" }],
      relevadores_label: "Fabian Esquivel",
      fecha: "2026-06-02",
      distrito_mostrar: "Centro",
    });
    expect(payload).toEqual({
      turno: "MANIANA",
      relevador_ids: [1],
      calle: "TestRelevamientoDomicilio_abc",
      numero: "123",
      numero_tipo: "NUMERO",
      angulo_esquina: null,
      rubro: "Panadería",
      nombre_fantasia: null,
      esta_abierto: true,
    });
    expect(payload).not.toHaveProperty("fecha");
    expect(payload).not.toHaveProperty("relevadores");
    expect(payload).not.toHaveProperty("relevadores_label");
  });

  it("REL-MAP-CIERRE.2-3.1: rubro vacío se normaliza a null en payload", () => {
    const normalized = normalizeRelevamientoRowForApi({
      ...baseRow,
      rubro: "",
    });
    expect(normalized.rubro).toBeNull();
    const payload = buildRelevamientoUpdatePayload(normalized);
    expect(payload.rubro).toBeNull();
  });

  it("REL-MAP-CIERRE.2-3: legacy multi omite relevador_ids del PUT", () => {
    const payload = buildRelevamientoUpdatePayload(baseRow, { omitRelevador: true });
    expect(payload.relevador_ids).toBeUndefined();
    expect(payload.calle).toBeTruthy();
  });

  it("ESQUINA → NUMERO envía numero_tipo NUMERO", () => {
    const baseline = {
      ...baseRow,
      numero_tipo: "ESQUINA",
      numero: "San Martín y Maipú",
      esquina_normalizada: "San Martín y Maipú",
    };
    const draft = {
      ...relevamientoRowParaEdicion(baseline),
      numero_tipo: "NUMERO",
      numero: "500",
    };
    const payload = applyRelevamientoDomicilioSubmitGuard(draft, baseline);
    expect(payload.numero_tipo).toBe("NUMERO");
    expect(payload.numero).toBe("500");
  });
});
