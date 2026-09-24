import * as XLSX from "xlsx-js-style";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  applyBlackBordersToWorksheet,
  writeStyledWorkbook,
} from "../../../utils/xlsxWorksheetBlackBorders";
import {
  buildActuacionesNormalizedExcelRows,
  type ActuacionNormalizedExcelRow,
} from "./actuacionesExportNormalizedRows";

function buildFileName(desde: string, hasta: string): string {
  return `actuaciones_${desde}_${hasta}.xlsx`;
}

/**
 * Descarga Excel normalizado de actuaciones (columnas atómicas + bordes negros en toda la grilla).
 */
export function downloadActuacionesExcel(
  items: IActuacionListItem[],
  range: { desde: string; hasta: string }
): void {
  const rows: ActuacionNormalizedExcelRow[] = buildActuacionesNormalizedExcelRows(items);
  const worksheet = XLSX.utils.json_to_sheet(rows);
  applyBlackBordersToWorksheet(worksheet);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Actuaciones");
  writeStyledWorkbook(workbook, buildFileName(range.desde, range.hasta));
}
