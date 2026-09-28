import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { GridRow } from "../../../api/gridApi";
import {
  buildInitialRelevamientoGridData,
  extractRelevamientoDataColumns,
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

  it("storage key aislada por usuario (v3)", () => {
    expect(relevamientoDraftStorageKey("alice")).toBe("digitaliza:relevamientos:draft:v3:alice");
    expect(relevamientoDraftStorageKey("bob")).not.toContain("alice");
  });

  it("draft v2 en key antigua no se rehidrata (nueva versión)", () => {
    sessionStorage.setItem(
      "digitaliza:relevamientos:draft:v2:user1",
      JSON.stringify({
        version: 2,
        drafts: [
          {
            clientRowId: "legacy",
            fields: { Calle: "Vieja", Numero: "1" },
          },
        ],
      })
    );
    expect(readRelevamientoDrafts("user1")).toEqual([]);
    expect(sessionStorage.getItem(relevamientoDraftStorageKey("user1"))).toBeNull();
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

describe("RELEVAMIENTO-HOTFIX.2B — rehidratación sin fecha", () => {
  beforeEach(() => {
    Object.keys(store).forEach((k) => delete store[k]);
    mockSessionStorage();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const fullRow = () =>
    draftRow({
      _rowId: "row_sin_fecha",
      Relevador: "Fabian Esquivel",
      Calle: "San Martín",
      Numero: "1009",
      Rubro: "Panadería",
      _relevadorIds: [1],
      _needsCommit: true,
      _touched: true,
    } as Partial<GridRow> & { _rowId: string });

  it("ciclo serialize → read → buildInitial sin Fecha ni fecha_actuacion", () => {
    const original = fullRow();
    writeRelevamientoDrafts("user1", [original]);
    const stored = serializeRelevamientoDraftRows([original]);
    expect(stored[0]?.fields.Fecha).toBeUndefined();
    expect(stored[0]?.fields).not.toHaveProperty("fecha_actuacion");

    const restored = buildInitialRelevamientoGridData(readRelevamientoDrafts("user1"))[0];
    expect(restored.Fecha).toBeUndefined();
    expect(restored).not.toHaveProperty("fecha_actuacion");
    expect(restored._state).toBe("PENDIENTE");
    expect(restored._cellErrors).toEqual({});
    expect(restored._rowError).toBeNull();
    expect(restored._normalized).toBeUndefined();
    expect(restored._needsCommit).toBe(true);
    expect(restored._touched).toBe(true);

    const payload = extractRelevamientoDataColumns(restored);
    expect(payload).not.toHaveProperty("fecha_actuacion");
    expect(payload).not.toHaveProperty("Fecha actuación");
    expect(payload).not.toHaveProperty("_needsCommit");
    expect(payload).not.toHaveProperty("_relevadorIds");
    expect(payload.Fecha).toBeUndefined();
    expect(payload).toMatchObject({
      Relevador: "Fabian Esquivel",
      Calle: "San Martín",
      Numero: "1009",
      Rubro: "Panadería",
    });
  });

  it("legacy fields en storage no se incorporan al GridRow", () => {
    const polluted = buildInitialRelevamientoGridData([
      {
        clientRowId: "polluted",
        fields: {
          Relevador: "Fabian Esquivel",
          Calle: "San Martín",
          Numero: "1009",
          Rubro: "Panadería",
          "Fecha actuación": "",
          fecha_actuacion: "",
          _cellErrors: { fecha_actuacion: "Fecha requerida" },
          _state: "ERROR",
        },
      },
    ])[0];

    expect(polluted).not.toHaveProperty("fecha_actuacion");
    expect(polluted).not.toHaveProperty("Fecha actuación");
    expect(polluted._cellErrors).toEqual({});
    expect(polluted._state).toBe("PENDIENTE");
    expect(polluted._normalized).toBeUndefined();
  });

  it("remount: persistir, limpiar memoria y volver a leer produce payload validable", () => {
    writeRelevamientoDrafts("user1", [fullRow()]);
    const afterUnmount = readRelevamientoDrafts("user1");
    const remounted = buildInitialRelevamientoGridData(afterUnmount)[0];
    const payload = extractRelevamientoDataColumns(remounted);
    expect(Object.keys(payload).sort()).toEqual(
      ["Calle", "Numero", "Relevador", "Rubro"].sort()
    );
  });
});

