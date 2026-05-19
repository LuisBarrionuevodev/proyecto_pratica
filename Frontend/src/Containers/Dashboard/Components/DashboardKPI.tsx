import { Box, Card, CardContent, Typography } from "@mui/material";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import type { ReactNode } from "react";

import {
  dashboardGlassCardSx,
  dashboardKpiLabelSx,
  dashboardKpiValueSx,
} from "../../../styles/DashboardStyles";
import type { Periodo } from "../../../types/periodos";

interface KPIProps {
  title: string;
  value: number | string;
  /** Si se omite, no se muestra la franja de tendencia (datos reales sin variación). */
  percentage?: number;
  icon: ReactNode;
  periodo: Periodo;
}

const KPI = ({ title, value, percentage, icon, periodo }: KPIProps) => {
  const labelPeriodo = {
    Semanal: "Semana",
    Mensual: "Mes",
    Trimestral: "Trimestre",
    Anual: "Año",
  };

  const showTrend = typeof percentage === "number";
  const isPositive = showTrend && percentage >= 0;

  return (
    <Card
      sx={{
        ...dashboardGlassCardSx,
        p: { xs: 1.75, sm: 2 },
      }}
    >
      <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          {icon}
          <Typography sx={dashboardKpiLabelSx}>{title}</Typography>
        </Box>

        <Typography sx={dashboardKpiValueSx}>{value}</Typography>

        {showTrend ? (
          <Box display="flex" alignItems="center" gap={0.5} mt={1}>
            {isPositive ? (
              <TrendingUpIcon sx={{ fontSize: 18, color: "success.main" }} />
            ) : (
              <TrendingDownIcon sx={{ fontSize: 18, color: "error.main" }} />
            )}
            <Typography
              variant="body2"
              sx={{
                color: isPositive ? "success.main" : "error.main",
                fontWeight: 600,
                fontFamily: '"Tactic Sans", sans-serif',
              }}
            >
              {percentage}%
            </Typography>
            <Typography variant="body2" sx={{ ...dashboardKpiLabelSx, fontWeight: 500 }}>
              {periodo === "Semanal" ? "Última" : "Último"} {labelPeriodo[periodo]}
            </Typography>
          </Box>
        ) : (
          <Typography variant="body2" sx={{ ...dashboardKpiLabelSx, mt: 1, fontWeight: 500 }}>
            {periodo === "Semanal" ? "Última" : "Último"} {labelPeriodo[periodo]}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default KPI;
