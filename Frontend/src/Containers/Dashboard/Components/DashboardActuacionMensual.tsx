import { BarChart } from "@mui/x-charts/BarChart";
import { ChartStyle } from "../../../styles/DashboardStyles";
import type { Periodo } from "../../../types/periodos";
import { useMemo } from "react";

interface Props {
  periodo: Periodo;
}


const ActuacionesMensualesChart =  ({periodo}: Props) => {
  const meses = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
  ];

  return (
    <BarChart
      xAxis={[{ scaleType: "band", data: meses }]}
      series={[
        {
          label: "Clausuras",
          data: [30, 40, 35, 50, 45, 60],
          stack: "total",
        },
        {
          label: "Notificaciones",
          data: [80, 70, 75, 90, 85, 95],
          stack: "total",
        },
        {
          label: "Inspecciones",
          data: [120, 130, 125, 140, 150, 160],
          stack: "total",
        },
      ]}
      height={350}
        sx={ChartStyle}
    />
  );
}

export default ActuacionesMensualesChart;
