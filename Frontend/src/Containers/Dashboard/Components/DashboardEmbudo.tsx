import { BarChart } from "@mui/x-charts";
import { ChartStyle } from "../../../styles/DashboardStyles";

const PipelineChart = () => {
  const etapas = [
    "Actuaciones",
    "Inspecciones",
    "Notificaciones",
    "Comprobaciones",
    "Clausuras",
    "Decomisos",
  ];

  return (
    <BarChart
      layout="horizontal"
      yAxis={[{ scaleType: "band", data: etapas }]}
      series={[
        {
          color:"#0166FF",
          data: [1000, 800, 650, 500, 300, 150],
          label: "Cantidad",
        },
      ]}
      height={400}
        sx={ChartStyle}
    />
  );
}

export default PipelineChart;
