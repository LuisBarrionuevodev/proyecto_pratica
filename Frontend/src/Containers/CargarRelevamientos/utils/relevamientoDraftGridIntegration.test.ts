import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { GridRow } from "../../../api/gridApi";
import {
  buildInitialRelevamientoGridData,
  extractRelevamientoDataColumns,
  readRelevamientoDrafts,
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

const validateBatch = vi.fn();
const commitBatch = vi.fn();

vi.mock("../../../api/gridApi", () => ({
  validateBatch: (...args: unknown[]) => validateBatch(...args),
  commitBatch: (...args: unknown[]) => commitBatch(...args),
}));

describe("RELEVAMIENTO-HOTFIX.2B — grid validate/commit tras remount", () => {
  beforeEach(() => {
    Object.keys(store).forEach((k) => delete store[k]);
    mockSessionStorage();
    validateBatch.mockReset();
    commitBatch.mockReset();
    validateBatch.mockResolvedValue({
      results: [
        {
          row_id: "row_sin_fecha",
          ok: true,
          errors: {},
          normalized: {
            fecha: "2026-09-28",
            relevador: "Fabian Esquivel",
            calle: "San Martín",
            numero: "1009",
            rubro: "Panadería",
          },
        },
      ],
    });
    commitBatch.mockResolvedValue({
      results: [
        {
          row_id: "row_sin_fecha",
          ok: true,
          persisted: { id: 42 },
        },
      ],
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it("payload post-remount no incluye fecha_actuacion y validate/commit OK", async () => {
    const row = {
      _rowId: "row_sin_fecha",
      _state: "PENDIENTE",
      _cellErrors: {},
      _touched: true,
      _needsCommit: true,
      Relevador: "Fabian Esquivel",
      Calle: "San Martín",
      Numero: "1009",
      Rubro: "Panadería",
    } as GridRow;

    writeRelevamientoDrafts("user1", [row]);
    const remounted = buildInitialRelevamientoGridData(readRelevamientoDrafts("user1"))[0];
    const payload = extractRelevamientoDataColumns(remounted);

    expect(payload).not.toHaveProperty("fecha_actuacion");
    expect(payload.Fecha).toBeUndefined();

    const { validateBatch: validateBatchApi, commitBatch: commitBatchApi } = await import(
      "../../../api/gridApi"
    );

    const batchId = "batch-test";
    const validateResp = await validateBatchApi({
      batch_id: batchId,
      kind: "relevamientos",
      rows: [{ row_id: remounted._rowId!, row: payload }],
    });
    expect(validateResp.results[0]?.ok).toBe(true);
    expect(validateBatch).toHaveBeenCalledWith({
      batch_id: batchId,
      kind: "relevamientos",
      rows: [
        {
          row_id: "row_sin_fecha",
          row: {
            Relevador: "Fabian Esquivel",
            Calle: "San Martín",
            Numero: "1009",
            Rubro: "Panadería",
          },
        },
      ],
    });

    const commitResp = await commitBatchApi({
      batch_id: batchId,
      kind: "relevamientos",
      rows: [
        {
          row_id: remounted._rowId!,
          normalized: validateResp.results[0]!.normalized!,
        },
      ],
    });
    expect(commitResp.results[0]?.ok).toBe(true);
    expect(commitResp.results[0]?.persisted?.id).toBe(42);
  });
});
