import { Box, Typography } from "@mui/material";
import { BarChart } from "@mui/x-charts";

import { ChartStyle, dashboardEmptyStateSx } from "../../../styles/DashboardStyles";
import { GLASS_COLORS } from "../../../styles/GlassStyles";

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
      <Box sx={dashboardEmptyStateSx}>
        <Typography variant="body2">Sin actuaciones en el periodo seleccionado.</Typography>
      </Box>
    );
  }

  const pctSin = Math.round((sinContraproducencia / total) * 100);
  const pctCon = Math.round((conContraproducencia / total) * 100);

  return (
    <Box>
      <Typography
        variant="caption"
        sx={{ display: "block", mb: 1, color: "text.secondary" }}
      >
        Total: {total} · Sin CP: {pctSin}% · Con CP: {pctCon}%
      </Typography>
      <BarChart
        sx={ChartStyle}
        slotProps={{ tooltip: { trigger: "item" } }}
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
            color: GLASS_COLORS.primary,
          },
        ]}
        height={260}
      />
    </Box>
  );
};

export default EfectivasInefectivasChart;
