import { PieChart } from "@mui/x-charts/PieChart";
import { ChartStyle } from "../../../styles/DashboardStyles";

const DistribucionTipoChart = () => {
  return (
    <PieChart
      series={[
        {
          data: [
            { id: 1, value: 30, label: "Inspecciones" },
            { id: 2, value: 30, label: "Reinspecciones" },
            { id: 3, value: 30, label: "Ratificacion de Clausura" },
            { id: 4, value: 30, label: "Ratificacion de Decomiso" },
            { id: 5, value: 30, label: "Verificar e Informar" },
            { id: 6, value: 30, label: "Transporte" },
          ],
        },
      ]}
      height={300}
        sx={ChartStyle}
    />
  );
}

export default DistribucionTipoChart;