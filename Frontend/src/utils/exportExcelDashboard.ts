import * as XLSX from "xlsx";
import { saveAs } from "file-saver";

// Interfaz opcional para tipar los datos
interface DashboardData {
  tarjetas: { title: string; value: number }[];
  lineChart: { mes: string; actu: number }[];
  pieChart: { rubro: string; clausuras: number }[];
}

export const exportDashboardToExcel = (data: DashboardData) => {
  const wb = XLSX.utils.book_new();

  // Hoja de Tarjetas
  const tarjetasWs = XLSX.utils.json_to_sheet(data.tarjetas);
  XLSX.utils.book_append_sheet(wb, tarjetasWs, "Tarjetas");

  // Hoja de LineChart
  const lineChartWs = XLSX.utils.json_to_sheet(data.lineChart);
  XLSX.utils.book_append_sheet(wb, lineChartWs, "Actuaciones x mes");

  // Hoja de PieChart
  const pieChartWs = XLSX.utils.json_to_sheet(data.pieChart);
  XLSX.utils.book_append_sheet(wb, pieChartWs, "Rubros");

  // Generar archivo
  const wbout = XLSX.write(wb, { bookType: "xlsx", type: "array" });
  saveAs(new Blob([wbout], { type: "application/octet-stream" }), "dashboard.xlsx");
};
