import { describe, expect, it } from "vitest";

import type { IRelevamientoListItem } from "../../../api/relevamientosListApi";
import {
  relevamientoAnguloChipLabel,
  relevamientoCalleDisplay,
  relevamientoEstaAbiertoDisplay,
  relevamientoEstablecimientoDisplay,
  relevamientoEstablecimientoLines,
  relevamientoNombreFantasiaDisplay,
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

  it("muestra nombre fantasía y ángulo solo si existen", () => {
    expect(relevamientoNombreFantasiaDisplay({ ...baseRow, nombre_fantasia: "  El Toro " })).toBe(
      "El Toro"
    );
    expect(relevamientoNombreFantasiaDisplay({ ...baseRow, nombre_fantasia: null })).toBeNull();
    expect(
      relevamientoAnguloChipLabel({
        ...baseRow,
        numero_tipo: "ESQUINA",
        angulo_esquina: "NE",
      })
    ).toBe("Esquina NE");
    expect(
      relevamientoAnguloChipLabel({ ...baseRow, numero_tipo: "NUMERO", angulo_esquina: "NE" })
    ).toBeNull();
  });

  it("establecimiento display combina rubro, fantasía y ángulo", () => {
    const lines = relevamientoEstablecimientoLines({
      ...baseRow,
      nombre_fantasia: "La Esquina",
      numero_tipo: "ESQUINA",
      angulo_esquina: "SO",
    });
    expect(lines.primary).toBe("Panadería");
    expect(lines.secondary).toContain("Nombre fantasía: La Esquina");
    expect(lines.anguloChip).toBe("Esquina SO");
    expect(relevamientoEstablecimientoDisplay({ ...baseRow })).toBe("Panadería");
  });

  it("legacy sin campos nuevos sigue renderizando rubro", () => {
    expect(relevamientoEstablecimientoLines(baseRow).primary).toBe("Panadería");
    expect(relevamientoEstablecimientoLines(baseRow).secondary).toBeNull();
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
