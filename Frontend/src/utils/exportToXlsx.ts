import type { MRT_ColumnDef, MRT_Row } from "material-react-table";
import * as XLSX from "xlsx";

type ExportToXlsxOptions = {
  rows: MRT_Row<any>[];
  columns: MRT_ColumnDef<any>[];
  fileName: string;
  sheetName?: string;
};

const isExportableColumn = (column: MRT_ColumnDef<any>) => {
  const col = column as MRT_ColumnDef<any> & { id?: string };
  const colId = String(col.id ?? col.accessorKey ?? "").trim();
  const header = String(col.header ?? "").trim().toLowerCase();

  if (!colId) return false;
  if (colId.startsWith("mrt-")) return false;
  if (colId === "acciones") return false;
  if (header === "actions" || header === "acciones") return false;

  return true;
};

const getColumnId = (column: MRT_ColumnDef<any>) => {
  const col = column as MRT_ColumnDef<any> & { id?: string };
  return String(col.id ?? col.accessorKey ?? "");
};

const getColumnHeader = (column: MRT_ColumnDef<any>) => {
  if (typeof column.header === "string") return column.header;
  const colId = getColumnId(column);
  return colId || "Columna";
};

const normalizeCellValue = (value: unknown): string | number | boolean => {
  if (value === null || value === undefined) return "";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return value;
  }
  if (value instanceof Date) {
    return value.toISOString().slice(0, 10);
  }
  if (Array.isArray(value) || typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
};

export function exportMrtRowsToXlsx({
  rows,
  columns,
  fileName,
  sheetName = "Datos",
}: ExportToXlsxOptions): void {
  const exportableColumns = columns.filter(isExportableColumn);
  const parsedRows = rows.map((row) => {
    const result: Record<string, string | number | boolean> = {};
    exportableColumns.forEach((column) => {
      const colId = getColumnId(column);
      const header = getColumnHeader(column);
      const rawValue = row.getValue(colId);
      result[header] = normalizeCellValue(rawValue);
    });
    return result;
  });

  const worksheet = XLSX.utils.json_to_sheet(parsedRows);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);

  const safeFileName = fileName.endsWith(".xlsx") ? fileName : `${fileName}.xlsx`;
  XLSX.writeFile(workbook, safeFileName);
}
