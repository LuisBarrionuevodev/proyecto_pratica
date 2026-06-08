import { Box } from "@mui/material";
import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  columns?: { xs?: string; sm?: string; md?: string; lg?: string };
  gap?: number | string;
};

/**
 * Grilla responsive para KPIs y métricas del dashboard analytics.
 */
export function DashboardMetricGrid({
  children,
  columns = {
    xs: "1fr 1fr",
    sm: "repeat(2, 1fr)",
    md: "repeat(3, 1fr)",
    lg: "repeat(3, 1fr)",
  },
  gap = 1.5,
}: Props) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: columns,
        gap,
        alignItems: "stretch",
      }}
    >
      {children}
    </Box>
  );
}
