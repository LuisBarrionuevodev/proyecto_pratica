import { Box, Card, CardContent, Typography } from "@mui/material";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import type { ReactNode } from "react";

import {
  dashboardGlassCardSx,
  dashboardKpiLabelSx,
  dashboardKpiValueCompactSx,
  dashboardKpiValueSx,
} from "../../../styles/DashboardStyles";
import type { Periodo } from "../../../types/periodos";

interface KPIProps {
  title: string;
  value: number | string;
  /** Si se omite, no se muestra la franja de tendencia (datos reales sin variación). */
  percentage?: number;
  icon?: ReactNode | null;
  periodo?: Periodo;
  /** KPI más bajo para grillas operativas / ejecutivas. */
  compact?: boolean;
  /** Muestra «Último mes» etc.; por defecto oculto (el rango lo define el filtro de fechas). */
  showPeriodFootnote?: boolean;
}

const KPI = ({
  title,
  value,
  percentage,
  icon = null,
  periodo = "Mensual",
  compact = false,
  showPeriodFootnote = false,
}: KPIProps) => {
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
        p: compact ? { xs: 1.25, sm: 1.35 } : { xs: 1.75, sm: 2 },
      }}
    >
      <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
        <Box display="flex" alignItems="center" gap={0.75} mb={compact ? 0.5 : 1}>
          {icon}
          <Typography sx={{ ...dashboardKpiLabelSx, fontSize: compact ? "0.7rem" : undefined }}>
            {title}
          </Typography>
        </Box>

        <Typography sx={compact ? dashboardKpiValueCompactSx : dashboardKpiValueSx}>{value}</Typography>

        {showTrend ? (
          <Box display="flex" alignItems="center" gap={0.5} mt={0.75}>
            {isPositive ? (
              <TrendingUpIcon sx={{ fontSize: 16, color: "success.main" }} />
            ) : (
              <TrendingDownIcon sx={{ fontSize: 16, color: "error.main" }} />
            )}
            <Typography
              variant="body2"
              sx={{
                color: isPositive ? "success.main" : "error.main",
                fontWeight: 600,
                fontFamily: '"Tactic Sans", sans-serif',
                fontSize: "0.75rem",
              }}
            >
              {percentage}%
            </Typography>
            {showPeriodFootnote ? (
              <Typography variant="body2" sx={{ ...dashboardKpiLabelSx, fontWeight: 500, fontSize: "0.7rem" }}>
                {periodo === "Semanal" ? "Última" : "Último"} {labelPeriodo[periodo]}
              </Typography>
            ) : null}
          </Box>
        ) : showPeriodFootnote ? (
          <Typography variant="body2" sx={{ ...dashboardKpiLabelSx, mt: 0.75, fontWeight: 500, fontSize: "0.7rem" }}>
            Período seleccionado
          </Typography>
        ) : null}
      </CardContent>
    </Card>
  );
};

export default KPI;
