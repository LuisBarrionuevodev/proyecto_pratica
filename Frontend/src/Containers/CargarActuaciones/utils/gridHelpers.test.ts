import { describe, expect, it } from "vitest";

import type { GridRow } from "../../../api/gridApi";
import { extractDataColumns } from "./gridHelpers";

describe("extractDataColumns", () => {
  it("excluye metadatos internos incluyendo _needsCommit y _relevadorIds", () => {
    const row = {
      _rowId: "r1",
      _state: "PENDIENTE",
      _cellErrors: { Calle: "x" },
      _rowError: "err",
      _normalized: { foo: 1 },
      _validation_history: [],
      _touched: true,
      _needsCommit: true,
      _relevadorIds: [1, 2],
      Calle: "San Martín",
      Numero: "1009",
    } as GridRow;

    const payload = extractDataColumns(row);
    expect(payload).toEqual({ Calle: "San Martín", Numero: "1009" });
    expect(payload).not.toHaveProperty("_needsCommit");
    expect(payload).not.toHaveProperty("_relevadorIds");
    expect(payload).not.toHaveProperty("fecha_actuacion");
  });
});
