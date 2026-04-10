import { Box, Typography } from "@mui/material";
import { BarChart } from "@mui/x-charts";
import { ChartStyle } from "../../../styles/DashboardStyles";

interface Props {
  sinContraproducencia: number;
  conContraproducencia: number;
}

/**
 * Comparación actuaciones sin / con contraproducencia (datos reales del resumen).
 */
const EfectivasInefectivasChart = ({ sinContraproducencia, conContraproducencia }: Props) => {
  const total = sinContraproducencia + conContraproducencia;
  if (total === 0) {
    return (
      <Box sx={{ height: 350, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Typography variant="body2" color="rgba(255,255,255,0.6)">
          Sin actuaciones en el periodo seleccionado.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: 350 }}>
      <BarChart
        sx={ChartStyle}
        slotProps={{
          tooltip: {
            trigger: "item",
          },
        }}
        xAxis={[
          {
            scaleType: "band",
            data: ["Sin contraproducencia", "Con contraproducencia"],
          },
        ]}
        series={[
          {
            label: "Actuaciones",
            data: [sinContraproducencia, conContraproducencia],
            color: "#22BF75",
          },
        ]}
        height={350}
      />
    </Box>
  );
};

export default EfectivasInefectivasChart;