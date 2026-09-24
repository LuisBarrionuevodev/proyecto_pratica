import * as XLSX from "xlsx-js-style";

import {
  applyBlackBordersToWorksheet,
  writeStyledWorkbook,
} from "../../../utils/xlsxWorksheetBlackBorders";
import type { ComprobacionExportRow, ComprobacionExportSlice } from "./comprobacionExportTypes";
import {
  buildComprobacionesNormalizedExcelRows,
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
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Comprobaciones");
  writeStyledWorkbook(workbook, buildFileName(range.desde, range.hasta));
}
