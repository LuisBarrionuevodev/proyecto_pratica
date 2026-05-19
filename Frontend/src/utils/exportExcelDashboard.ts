import * as XLSX from "xlsx";
import { saveAs } from "file-saver";

/** Solo KPIs reales del resumen — sin series mock (D1b). */
interface DashboardExportData {
  tarjetas: { title: string; value: number }[];
  periodoLabel?: string;
}

/**
 * Exporta únicamente tarjetas/KPIs con datos del servidor.
 * Gráficos demo no se incluyen hasta D1c/D1d.
 */
export const exportDashboardToExcel = (data: DashboardExportData) => {
  const wb = XLSX.utils.book_new();

  const tarjetasRows: { Indicador: string; Valor: string | number }[] = [];
  if (data.periodoLabel) {
    tarjetasRows.push({ Indicador: "Periodo", Valor: data.periodoLabel });
  }
  tarjetasRows.push(
    ...data.tarjetas.map((t) => ({
      Indicador: t.title,
      Valor: t.value,
    }))
  );

  const tarjetasWs = XLSX.utils.json_to_sheet(tarjetasRows);
  XLSX.utils.book_append_sheet(wb, tarjetasWs, "Indicadores");

  const wbout = XLSX.write(wb, { bookType: "xlsx", type: "array" });
  saveAs(new Blob([wbout], { type: "application/octet-stream" }), "indicadores-resumen.xlsx");
};
