import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import type { GridRow } from "../../../api/gridApi";
import { extractRelevamientoDataColumns } from "./relevamientoDraftSessionStorage";

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), "utf8");

/**
 * Simula el flujo ref-first: última edición en ref antes de armar payload de validate.
 */
function buildValidatePayloadFromRef(
  dataRef: { current: GridRow[] },
  rowIndex: number,
  columnId: string,
  value: string
) {
  const rowData = dataRef.current[rowIndex];
  const updatedRow: GridRow = {
    ...rowData,
    [columnId]: value,
    _touched: true,
    _needsCommit: true,
  };
  const nextData = [...dataRef.current];
  nextData[rowIndex] = updatedRow;
  dataRef.current = nextData;
  return {
    row_id: updatedRow._rowId!,
    row: extractRelevamientoDataColumns(updatedRow),
  };
}

describe("HOTFIX V1.1-OPER.1 — relevamiento submit snapshot", () => {
  const glideSrc = read(
    "src/Containers/CargarRelevamientos/Components/TablaCargarRelevamientosGlideStyled.tsx"
  );

  it("handleCellEdit y batch usan dataRef como fuente de verdad", () => {
    expect(glideSrc).toContain("const replaceGridRows = useCallback");
    expect(glideSrc).toContain("dataRef.current = nextData");
    expect(glideSrc).toContain("const rowData = dataRef.current[row]");
    expect(glideSrc).toContain("const rowsToValidate = dataRef.current.filter");
    const handleCellEditBlock = glideSrc.slice(
      glideSrc.indexOf("const handleCellEdit = useCallback"),
      glideSrc.indexOf("const focusGridCell = useCallback")
    );
    expect(handleCellEditBlock).not.toMatch(/const rowData = data\[row\]/);
  });

  it("última edición de celda queda en el payload de validate sin esperar render", () => {
    const dataRef = {
      current: [
        {
          _rowId: "r1",
          Relevador: "Ana",
          Calle: "Mitre",
          Numero: "10",
          Rubro: "Panadería",
        } as GridRow,
      ],
    };
    const payload = buildValidatePayloadFromRef(dataRef, 0, "Rubro", "Carnicería");
    expect(payload.row.Rubro).toBe("Carnicería");
    expect(dataRef.current[0].Rubro).toBe("Carnicería");
  });

  it("validate sin Fecha en UI usa normalized.fecha efectivo en commit", () => {
    const normalized = {
      fecha: "2026-10-02",
      relevador: "Ana",
      calle: "Mitre",
      numero: "10",
      rubro: "Carnicería",
    };
    const row = {
      _rowId: "r1",
      Relevador: "Ana",
      Calle: "Mitre",
      Numero: "10",
      Rubro: "Carnicería",
    } as GridRow;
    const payload = extractRelevamientoDataColumns(row);
    expect(payload).not.toHaveProperty("fecha_actuacion");
    expect(payload.Fecha).toBeUndefined();
    expect(normalized.fecha).toBeTruthy();
  });
});
