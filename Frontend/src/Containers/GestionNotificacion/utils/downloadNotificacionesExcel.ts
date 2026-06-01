import * as XLSX from "xlsx-js-style";

import type { IActuacionesPendientesItem } from "../../../api/actuacionesPendientesApi";
import {
  applyBlackBordersToWorksheet,
  writeStyledWorkbook,
} from "../../../utils/xlsxWorksheetBlackBorders";
import type { PlazoOperativoSlice } from "../gestionNotificacionPlazo";
import {
  buildNotificacionesNormalizedExcelRows,
  type NotificacionNormalizedExcelRow,
} from "./notificacionesExportNormalizedRows";

function buildFileName(desde: string, hasta: string): string {
  return `notificaciones_${desde}_${hasta}.xlsx`;
}

/**
 * Descarga Excel normalizado de notificaciones (columnas atómicas + bordes negros).
 */
export function downloadNotificacionesExcel(
  items: IActuacionesPendientesItem[],
  range: { desde: string; hasta: string },
  plazoSlice: PlazoOperativoSlice
): void {
  const rows: NotificacionNormalizedExcelRow[] = buildNotificacionesNormalizedExcelRows(items, plazoSlice);
  const worksheet = XLSX.utils.json_to_sheet(rows);
  applyBlackBordersToWorksheet(worksheet);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Notificaciones");
  writeStyledWorkbook(workbook, buildFileName(range.desde, range.hasta));
}
