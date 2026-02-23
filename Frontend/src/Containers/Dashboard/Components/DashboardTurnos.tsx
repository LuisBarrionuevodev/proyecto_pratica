import { BarChart } from "@mui/x-charts";
import { ChartStyle } from "../../../styles/DashboardStyles";

const ComparacionTurnoChart = () => {
  return (
    <BarChart
      xAxis={[{ scaleType: "band", data: ["Mañana", "Tarde",] }]}
      series={[
        {
          label: "Actuaciones",
          color:"#0166FF",
          data: [200, 300,],
        },
      ]}
      height={350}
        sx={ChartStyle}
    />
  );
}

export default ComparacionTurnoChart;