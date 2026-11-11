import * as XLSX from "xlsx-js-style";

import {
  applyBlackBordersToWorksheet,
  writeStyledWorkbook,
} from "../../../utils/xlsxWorksheetBlackBorders";
import type { ComprobacionExportRow, ComprobacionExportSlice } from "./comprobacionExportTypes";
import {
  buildComprobacionesNormalizedExcelRows,
  RECORRIDO_EXCEL_COL_WIDTHS,
  type ComprobacionNormalizedExcelRow,
} from "./comprobacionesExportNormalizedRows";

function buildFileName(desde: string, hasta: string): string {
  return `comprobaciones_${desde}_${hasta}.xlsx`;
}

/**
 * Descarga Excel normalizado de actas de comprobación (columnas atómicas + bordes negros).
 */
export function downloadComprobacionesExcel(
  items: ComprobacionExportRow[],
  range: { desde: string; hasta: string },
  slice: ComprobacionExportSlice
): void {
  const rows: ComprobacionNormalizedExcelRow[] = buildComprobacionesNormalizedExcelRows(items, slice);
  const worksheet = XLSX.utils.json_to_sheet(rows);
  applyBlackBordersToWorksheet(worksheet);
  if (slice === "recorrido") {
    applyRecorridoExcelPresentation(worksheet);
  }
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Comprobaciones");
  writeStyledWorkbook(workbook, buildFileName(range.desde, range.hasta));
}

function applyRecorridoExcelPresentation(worksheet: XLSX.WorkSheet): void {
  const ref = worksheet["!ref"];
  if (!ref) return;
  const range = XLSX.utils.decode_range(ref);
  worksheet["!autofilter"] = { ref };
  worksheet["!views"] = [{ state: "frozen", ySplit: 1, topLeftCell: "A2", activeCell: "A2" }];
  worksheet["!cols"] = RECORRIDO_EXCEL_COL_WIDTHS.map((wch) => ({ wch }));
  for (let R = range.s.r; R <= range.e.r; R += 1) {
    for (let C = range.s.c; C <= range.e.c; C += 1) {
      const addr = XLSX.utils.encode_cell({ r: R, c: C });
      const cell = worksheet[addr];
      if (!cell) continue;
      cell.s = {
        ...(cell.s ?? {}),
        alignment: { wrapText: true, vertical: "top" },
      };
    }
  }
}
