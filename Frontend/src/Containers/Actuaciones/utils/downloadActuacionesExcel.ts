import * as XLSX from "xlsx";

import type { IActuacionListItem } from "../../../api/actuacionesListApi";
import {
  buildActuacionesNormalizedExcelRows,
  type ActuacionNormalizedExcelRow,
} from "./actuacionesExportNormalizedRows";

function buildFileName(desde: string, hasta: string): string {
  return `actuaciones_${desde}_${hasta}.xlsx`;
}

/**
 * Descarga Excel normalizado de actuaciones (columnas atómicas administrativas).
 */
export function downloadActuacionesExcel(
  items: IActuacionListItem[],
  range: { desde: string; hasta: string }
): void {
  const rows: ActuacionNormalizedExcelRow[] = buildActuacionesNormalizedExcelRows(items);
  const worksheet = XLSX.utils.json_to_sheet(rows);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Actuaciones");
  XLSX.writeFile(workbook, buildFileName(range.desde, range.hasta));
}
