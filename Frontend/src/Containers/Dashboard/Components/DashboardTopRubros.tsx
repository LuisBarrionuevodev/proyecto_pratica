import { BarChart } from "@mui/x-charts/BarChart";
import { ChartStyle } from "../../../styles/DashboardStyles";

const TopRubrosChart = () => {
  const rubros = [
    "Alimentos",
    "Kiosco",
    "Carnicería",
    "Supermercado",
    "Bebidas",
  ];

  return (
    <BarChart
      layout="horizontal"
      yAxis={[{ scaleType: "band", data: rubros,
       }]}
      
      series={[
        {
          color:"#0166FF",
          data: [120, 95, 80, 70, 60],
          label: "Actuaciones",
          
        },
      ]}
      height={350}
      sx={ChartStyle}
      
    />
  );
}

export default TopRubrosChart;
