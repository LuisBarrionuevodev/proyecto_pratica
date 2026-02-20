import { PieChart } from "@mui/x-charts/PieChart";
import { ChartStyle } from "../../../styles/DashboardStyles";

const DistribucionTipoChart = () => {
  return (
    <PieChart
      series={[
        {
          data: [
            { id: 0, value: 40, label: "Clausuras" },
            { id: 1, value: 30, label: "Notificaciones" },
            { id: 2, value: 20, label: "Inspecciones" },
            { id: 3, value: 10, label: "Decomisos" },
          ],
        },
      ]}
      height={300}
        sx={ChartStyle}
    />
  );
}

export default DistribucionTipoChart;