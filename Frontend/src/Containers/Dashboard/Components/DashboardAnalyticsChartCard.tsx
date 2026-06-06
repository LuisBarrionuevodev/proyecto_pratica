import { Box, Card, LinearProgress, Typography } from "@mui/material";
import type { ReactNode } from "react";

import {
  dashboardAnalyticsCardSx,
  dashboardAnalyticsChartTitleSx,
} from "../../../styles/DashboardStyles";

type Props = {
  title: string;
  children: ReactNode;
  loading?: boolean;
  /** Iguala altura mínima entre cards de una fila (riesgo). */
  fillHeight?: boolean;
};

/**
 * Contenedor chart/table estilo MUI Dashboard (dark analytics).
 */
export function DashboardAnalyticsChartCard({
  title,
  children,
  loading = false,
  fillHeight = false,
}: Props) {
  return (
    <Card
      sx={{
        ...dashboardAnalyticsCardSx,
        p: { xs: 1.25, sm: 1.5 },
        position: "relative",
        overflow: "hidden",
        minWidth: 0,
        width: "100%",
        height: fillHeight ? "100%" : "auto",
        display: fillHeight ? "flex" : "block",
        flexDirection: fillHeight ? "column" : undefined,
      }}
    >
      {loading ? (
        <LinearProgress
          sx={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, borderRadius: 0 }}
        />
      ) : null}
      <Typography component="h3" sx={dashboardAnalyticsChartTitleSx}>
        {title}
      </Typography>
      <Box
        sx={{
          flex: fillHeight ? 1 : undefined,
          opacity: loading ? 0.72 : 1,
          transition: "opacity 0.2s",
          minHeight: 0,
        }}
      >
        {children}
      </Box>
    </Card>
  );
}
