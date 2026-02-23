import { BarChart } from "@mui/x-charts";
import { ChartStyle } from "../../../styles/DashboardStyles";

const PipelineChart = () => {
  const etapas = [
    "Oficios",
    "Notificaciones",
  ];

  return (
    <BarChart
      xAxis={[{ scaleType: "band", data: etapas }]}
      series={[
        {
          color:"#0166FF",
          data: [600, 400],
          label: "Cantidad",
        },
      ]}
      height={400}
        sx={ChartStyle}
    />
  );
}

export default PipelineChart;
