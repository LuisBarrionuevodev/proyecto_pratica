import { LineChart } from "@mui/x-charts/LineChart";
import { ChartStyle } from "../../../styles/DashboardStyles";

const DecomisoMensualChart = () => {
  return (
    <LineChart
      xAxis={[{ scaleType: "point", data: ["Ene", "Feb", "Mar", "Abr", "May", "Jun"] }]}
      series={[
        {
          color:"#0166FF",
          label: "Kg decomisados",
          data: [200, 350, 300, 450, 500, 600],
        },
      ]}
      height={300}
      sx={ChartStyle}
    />
  );
}

export default DecomisoMensualChart;
