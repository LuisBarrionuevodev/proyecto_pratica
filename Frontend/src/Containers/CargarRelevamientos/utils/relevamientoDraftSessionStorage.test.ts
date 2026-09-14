import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { GridRow } from "../../../api/gridApi";
import {
  buildInitialRelevamientoGridData,
  isMeaningfulRelevamientoDraft,
  readRelevamientoDrafts,
  relevamientoDraftStorageKey,
  serializeRelevamientoDraftRows,
  writeRelevamientoDrafts,
} from "./relevamientoDraftSessionStorage";

const store: Record<string, string> = {};

function mockSessionStorage() {
  vi.stubGlobal("sessionStorage", {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      Object.keys(store).forEach((k) => delete store[k]);
    },
    key: () => null,
    length: 0,
  });
}

function draftRow(partial: Partial<GridRow> & { _rowId: string }): GridRow {
  return {
    _state: "PENDIENTE",
    _cellErrors: {},
    _touched: true,
    ...partial,
  } as GridRow;
}

describe("relevamientoDraftSessionStorage", () => {
  beforeEach(() => {
    Object.keys(store).forEach((k) => delete store[k]);
    mockSessionStorage();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("storage key aislada por usuario", () => {
    expect(relevamientoDraftStorageKey("alice")).toBe("digitaliza:relevamientos:draft:v2:alice");
    expect(relevamientoDraftStorageKey("bob")).not.toContain("alice");
  });

  it("fila vacía no se persiste; con domicilio sí", () => {
    expect(isMeaningfulRelevamientoDraft(draftRow({ _rowId: "r1" }))).toBe(false);
    expect(
      isMeaningfulRelevamientoDraft(
        draftRow({ _rowId: "r2", Calle: "San Martín", _touched: true })
      )
    ).toBe(true);
    expect(
      isMeaningfulRelevamientoDraft(
        draftRow({ _rowId: "r3", "Está abierto": false, _touched: true })
      )
    ).toBe(true);
  });

  it("fila persistida (ID) no es draft", () => {
    expect(
      isMeaningfulRelevamientoDraft(
        draftRow({ _rowId: "r3", ID: 99, Relevador: "Fabian Esquivel", _touched: true })
      )
    ).toBe(false);
  });

  it("persist A/B/C y remount restaura", () => {
    const rows = [
      draftRow({ _rowId: "a", Relevador: "Fabian Esquivel", _touched: true }),
      draftRow({ _rowId: "b", Calle: "B", _touched: true }),
      draftRow({ _rowId: "c", Rubro: "C", _touched: true }),
    ];
    writeRelevamientoDrafts("user1", rows);
    const restored = readRelevamientoDrafts("user1");
    expect(restored.map((d) => d.clientRowId)).toEqual(["a", "b", "c"]);
    const grid = buildInitialRelevamientoGridData(restored);
    expect(grid[0]._rowId).toBe("a");
    expect(grid[1]._rowId).toBe("b");
    expect(grid[2]._rowId).toBe("c");
  });

  it("éxito parcial: solo queda la fila no guardada", () => {
    const rows = [
      draftRow({ _rowId: "a", Relevador: "Fabian Esquivel", _touched: true }),
      draftRow({ _rowId: "b", Relevador: "Otro", _touched: true }),
      draftRow({ _rowId: "c", Relevador: "Tercero", _touched: true }),
    ];
    writeRelevamientoDrafts("user1", rows);

    const afterPartial = [
      { ...rows[0], ID: 1, _state: "OK" as const, _touched: false },
      rows[1],
      { ...rows[2], ID: 3, _state: "OK" as const, _touched: false },
    ];
    writeRelevamientoDrafts("user1", afterPartial);

    const remaining = readRelevamientoDrafts("user1");
    expect(remaining).toHaveLength(1);
    expect(remaining[0]?.clientRowId).toBe("b");
  });

  it("usuario 2 no ve drafts de usuario 1", () => {
    writeRelevamientoDrafts("user1", [
      draftRow({ _rowId: "a", Relevador: "Fabian Esquivel", _touched: true }),
    ]);
    expect(readRelevamientoDrafts("user2")).toEqual([]);
  });

  it("borrado manual: fila eliminada no reaparece", () => {
    writeRelevamientoDrafts("user1", [
      draftRow({ _rowId: "a", Relevador: "Fabian Esquivel", _touched: true }),
    ]);
    writeRelevamientoDrafts("user1", []);
    expect(readRelevamientoDrafts("user1")).toEqual([]);
    expect(sessionStorage.getItem(relevamientoDraftStorageKey("user1"))).toBeNull();
  });

  it("JSON corrupto se ignora y limpia", () => {
    sessionStorage.setItem(relevamientoDraftStorageKey("user1"), "{not-json");
    expect(readRelevamientoDrafts("user1")).toEqual([]);
    expect(sessionStorage.getItem(relevamientoDraftStorageKey("user1"))).toBeNull();
  });

  it("serialize usa clientRowId estable", () => {
    const serialized = serializeRelevamientoDraftRows([
      draftRow({ _rowId: "stable-id", Calle: "Maipú", _touched: true }),
    ]);
    expect(serialized[0]?.clientRowId).toBe("stable-id");
    expect(serialized[0]?.fields).toEqual({ Calle: "Maipú" });
  });
});
