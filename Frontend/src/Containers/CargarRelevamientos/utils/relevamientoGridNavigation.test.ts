import { describe, expect, it } from "vitest";

import { COLUMN_DEFINITIONS } from "../config/columnDefinitions";
import {
  RELEVAMIENTO_FIRST_EDITABLE_COL_INDEX,
  RELEVAMIENTO_LAST_EDITABLE_COL_INDEX,
  RELEVAMIENTO_PENULTIMATE_EDITABLE_COL_INDEX,
  relevamientoDataColGridCell,
  relevamientoInspectorGridCell,
  relevamientoLastEditableGridCell,
  relevamientoResolveTabDataCol,
  resolveRelevamientoShiftTabBackwardStep,
  resolveRelevamientoTabForwardStep,
} from "./relevamientoGridNavigation";

describe("relevamientoGridNavigation", () => {
  it("Turno es penúltima; Está abierto es última", () => {
    expect(COLUMN_DEFINITIONS[RELEVAMIENTO_PENULTIMATE_EDITABLE_COL_INDEX]?.id).toBe("Turno");
    expect(COLUMN_DEFINITIONS[RELEVAMIENTO_LAST_EDITABLE_COL_INDEX]?.id).toBe("Está abierto");
  });

  it("prioriza gridSelection sobre event.location (evita saltar Está abierto)", () => {
    expect(relevamientoResolveTabDataCol([7, 0], [6, 0])).toEqual({ dataCol: 6, row: 0 });
    expect(relevamientoResolveTabDataCol([7, 0], [7, 0])).toEqual({ dataCol: 7, row: 0 });
  });

  describe("TAB forward", () => {
    it("Turno → Está abierto misma fila", () => {
      const step = resolveRelevamientoTabForwardStep(RELEVAMIENTO_PENULTIMATE_EDITABLE_COL_INDEX, 0, 5);
      expect(step).toEqual({ type: "next-col", dataCol: 7, row: 0 });
      expect(relevamientoDataColGridCell(7, 0)).toEqual([7, 0]);
    });

    it("columnas intermedias (no Turno/Está abierto) no interceptan", () => {
      expect(resolveRelevamientoTabForwardStep(0, 0, 5)).toBeNull();
      expect(resolveRelevamientoTabForwardStep(3, 2, 5)).toBeNull();
    });

    it("Está abierto fila 1 → Inspector fila 2", () => {
      expect(resolveRelevamientoTabForwardStep(RELEVAMIENTO_LAST_EDITABLE_COL_INDEX, 0, 5)).toEqual({
        type: "next-row-first-col",
        row: 1,
      });
      expect(relevamientoInspectorGridCell(1)).toEqual([0, 1]);
    });

    it("Está abierto última fila → append", () => {
      expect(
        resolveRelevamientoTabForwardStep(RELEVAMIENTO_LAST_EDITABLE_COL_INDEX, 4, 5)
      ).toEqual({ type: "append-row-first-col" });
    });
  });

  describe("SHIFT+TAB backward", () => {
    it("Está abierto → Turno", () => {
      expect(resolveRelevamientoShiftTabBackwardStep(7, 0)).toEqual({
        type: "prev-col",
        dataCol: 6,
        row: 0,
      });
    });

    it("Inspector fila 2 → Está abierto fila 1", () => {
      expect(resolveRelevamientoShiftTabBackwardStep(RELEVAMIENTO_FIRST_EDITABLE_COL_INDEX, 1)).toEqual({
        type: "prev-row-last-col",
        row: 0,
      });
      expect(relevamientoLastEditableGridCell(0)).toEqual([7, 0]);
    });
  });
});
