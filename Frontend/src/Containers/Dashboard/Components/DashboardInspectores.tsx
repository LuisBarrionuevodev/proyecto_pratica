import { BarChart } from "@mui/x-charts";
import { ChartStyle } from "../../../styles/DashboardStyles";

const RankingInspectoresChart = () => {
  const inspectores = [
    "Castro",
    "Diaz",
    "Gomez",
    "Ricciuti",
  ];

  return (
    <BarChart
      layout="horizontal"
      yAxis={[{ scaleType: "band", data: inspectores, width:50 }]}
      series={[
        {
          color:"#0166FF",
          data: [150, 120, 95, 80],
          label: "Actuaciones",
        },
      ]}
      height={350}
      sx={ChartStyle}
    />
  );
}

export default RankingInspectoresChart;
