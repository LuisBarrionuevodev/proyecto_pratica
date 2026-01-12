
import { mkConfig, generateCsv, download } from "export-to-csv";

export const csvConfig = mkConfig({
  fieldSeparator: ",",
  decimalSeparator: ".",
  useKeysAsHeaders: true,
});

export const exportVisibleRows = (rows: any[], table: any) => {
  const visibleColumns = table
    .getAllLeafColumns()
    .filter((col: { getIsVisible: () => any; }) => col.getIsVisible())
    .map((col: { id: any; }) => col.id);

  const rowData = rows.map((row) => {
    const filtered: Record<string, string | number | boolean> = {};
    visibleColumns.forEach((colId: string | number) => {
      filtered[colId] = (row.original as any)[colId];
    });
    return filtered;
  });

  const csv = generateCsv(csvConfig)(rowData);
  download(csvConfig)(csv);
};

export const exportAllData = (data: any[]) => {
  const csv = generateCsv(csvConfig)(data);
  download(csvConfig)(csv);
};







