import { Box } from "@mui/material";
import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  /** Columnas del grid de KPIs (default 4 ejecutivos). */
  columns?: { xs?: string; sm?: string; lg?: string };
};

/**
 * Grilla compacta para KPIs ejecutivos u operativos.
 */
export function DashboardExecutiveKpiGrid({
  children,
  columns = { xs: "1fr 1fr", sm: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" },
}: Props) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: columns,
        gap: 1.25,
        alignItems: "stretch",
      }}
    >
      {children}
    </Box>
  );
}
