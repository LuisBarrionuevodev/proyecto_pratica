import * as XLSX from "xlsx-js-style";

const THIN_BLACK_BORDER = {
  style: "thin" as const,
  color: { rgb: "000000" },
};

export type ApplyXlsxBlackBordersOptions = {
  /** Fila 0-based del encabezado (default 0). */
  headerRowIndex?: number;
  /** Encabezado con fondo negro y texto blanco (default true). */
  styleHeaderRow?: boolean;
};

/**
 * Aplica borde negro fino a todas las celdas del rango `!ref` de la hoja.
 * Requiere `xlsx-js-style` al escribir el libro (`writeStyledWorkbook`).
 */
export function applyBlackBordersToWorksheet(
  worksheet: XLSX.WorkSheet,
  options?: ApplyXlsxBlackBordersOptions
): void {
  const headerRow = options?.headerRowIndex ?? 0;
  const styleHeader = options?.styleHeaderRow !== false;
  const ref = worksheet["!ref"];
  if (!ref) return;

  const range = XLSX.utils.decode_range(ref);

  for (let R = range.s.r; R <= range.e.r; R += 1) {
    for (let C = range.s.c; C <= range.e.c; C += 1) {
      const addr = XLSX.utils.encode_cell({ r: R, c: C });
      const cell = worksheet[addr] ?? { t: "s", v: "" };
      worksheet[addr] = cell;

      const isHeader = styleHeader && R === headerRow;
      cell.s = {
        border: {
          top: THIN_BLACK_BORDER,
          bottom: THIN_BLACK_BORDER,
          left: THIN_BLACK_BORDER,
          right: THIN_BLACK_BORDER,
        },
        ...(isHeader
          ? {
              fill: { fgColor: { rgb: "000000" }, patternType: "solid" },
              font: { bold: true, color: { rgb: "FFFFFF" } },
            }
          : {}),
      };
    }
  }
}

/** Escribe un libro con estilos de celda (bordes, encabezado). */
export function writeStyledWorkbook(workbook: XLSX.WorkBook, fileName: string): void {
  XLSX.writeFile(workbook, fileName);
}
